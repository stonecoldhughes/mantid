# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +

import os

from mantid.api import PythonAlgorithm, MatrixWorkspaceProperty, MultipleFileProperty, Progress
from mantid.kernel import Direction, IntBoundedValidator, StringListValidator
from mantid.simpleapi import *

NUMBER_OF_PIXEL_PER_SPECTRO_TUBE = 128
NUMBER_OF_PIXEL_PER_DIFF_TUBE = 256


class IndirectILLReductionDIFF(PythonAlgorithm):
    """
    Performs reduction on IN16B's diffraction data. It can be on mode Doppler or BATS.
    """

    runs = None
    mode = None
    scan_parameter = None
    mask_start_pixels = None
    mask_end_pixels = None
    epp = None
    output = None
    progress = None
    instrument_name = None
    pulse_chopper = None
    reflection = None
    analyser = None
    instrument_ws = None

    def category(self):
        return "ILL\\Indirect"

    def summary(self):
        return "Performs reduction on IN16B's diffraction data. Mode is either Doppler or BATS."

    def name(self):
        return "IndirectILLReductionDIFF"

    def setUp(self):
        self.runs = self.getPropertyValue('SampleRuns').split(',')
        self.scan_parameter = self.getPropertyValue('Observable')
        self.mask_start_pixels = self.getProperty('MaskPixelsFromStart').value
        self.mask_end_pixels = self.getProperty('MaskPixelsFromEnd').value
        self.epp = mtd[self.getProperty('ElasticPeakPosition').value]
        self.pulse_chopper = self.getPropertyValue('PulseChopper')
        self.reflection = self.getPropertyValue('Reflection')
        self.analyser = self.getPropertyValue('Analyser')
        self.output = self.getPropertyValue('OutputWorkspace')
        self.progress = Progress(self, start=0.0, end=1.0, nreports=10)

    def PyInit(self):
        self.declareProperty(MultipleFileProperty('SampleRuns', extensions=['nxs']), doc="File path for run(s).")

        self.declareProperty(MatrixWorkspaceProperty('OutputWorkspace', '', direction=Direction.Output),
                             doc='The output workspace group containing reduced data.')

        self.declareProperty("MaskPixelsFromStart", 10, validator=IntBoundedValidator(lower=0),
                             doc="Number of pixels to mask at the start of each tube")
        self.declareProperty("MaskPixelsFromEnd", 10, validator=IntBoundedValidator(lower=0),
                             doc="Number of pixels to mask at the end of each tube")

        self.declareProperty("Observable", "sample.temperature",
                             doc="If multiple files, the parameter from SampleLog to use as an index when conjoined.")

        self.declareProperty("ElasticPeakPosition", "", doc="The result of a previous run, for configuration purpose")

        self.declareProperty(name='Analyser',
                             defaultValue='silicon',
                             validator=StringListValidator(['silicon']),
                             doc='Analyser crystal.')

        self.declareProperty(name='Reflection',
                             defaultValue='111',
                             validator=StringListValidator(['111', '311']),
                             doc='Analyser reflection.')

        self.declareProperty(name='PulseChopper', defaultValue='Auto',
                             validator=StringListValidator(['Auto', '12', '34']),
                             doc='Define the pulse chopper.')

    def _clean_bats(self):
        DeleteWorkspace(self.instrument_ws)

    def _normalize_by_monitor(self, ws):
        """
            Normalizes the workspace by monitor values (ID is 0 for IN16B)
            @param ws : the input workspace
        """
        monitor_ws = ws + '_mon'
        ExtractMonitors(InputWorkspace=ws, DetectorWorkspace=ws, MonitorWorkspace=monitor_ws)

        # in case of 0 counts monitors, replace 0s by 1s so the division becomes neutral
        # (since it's generally division of 0 detector's counts by 0 monitor's counts,
        # they weren't very useful to begin with)
        ReplaceSpecialValues(InputWorkspace=monitor_ws, OutputWorkspace=monitor_ws, SmallNumberThreshold=0.00000001,
                             SmallNumberValue=1)

        Divide(LHSWorkspace=ws, RHSWorkspace=monitor_ws, OutputWorkspace=ws, WarnOnZeroDivide=True)

        cache = list(range(1, self.mask_start_pixels)) + list(range(257 - self.mask_end_pixels, 257))
        to_mask = [i + 256 * j for i in cache for j in range(8)]
        MaskDetectors(Workspace=ws, DetectorList=to_mask)
        DeleteWorkspace(monitor_ws)

    def _get_pulse_chopper_info(self, run):
        """
        Retrieves information on pulse chopper pair.
        In low repetition mode pulse chopper and trigger chopper are not the same.
        In high repetition mode pulse trigger is always 1.
        @param run : the run of workspace
        @return : pulse chopper speed, pulse chopper phase, source distance
        """
        pulse_index = 1
        distance = 0.
        if self.pulse_chopper == 'Auto':
            if run.hasProperty('monitor.master_pickup'):
                trigger = run.getLogData('monitor.master_pickup').value
                if not 1 <= trigger <= 4:
                    self.log().information('Unexpected trigger chopper '+str(trigger))
                else:
                    if trigger == 1 or trigger == 2:
                        # and low repetition rate
                        pulse_index = 3
                        distance = 33.388
        elif self.pulse_chopper == '34':
            pulse_index = 3
            distance = 33.388

        chopper_speed_param = 'CH{0}.rotation_speed'.format(pulse_index)
        chopper_phase_param = 'CH{0}.phase'.format(pulse_index)

        if not run.hasProperty(chopper_speed_param) or not run.hasProperty(chopper_phase_param):
            raise RuntimeError('Unable to retrieve the pulse chopper speed and phase.')
        else:
            speed = run.getLogData(chopper_speed_param).value
            phase = run.getLogData(chopper_phase_param).value

        return speed, phase, distance

    def _find_spectrometer_t0(self, v_fixed):
        """
        Computes the tof on the l2 distance of the spectrometer detectors, and this distance at the equator.
        @param v_fixed the fixed velocity
        @return the time of flight along the l2 distance at the equator of the spectrometer, and this l2 distance
        """
        detector_info = self.instrument_ws.detectorInfo()

        number_of_pixels_per_tube = 128
        middle = number_of_pixels_per_tube // 2

        l2_equator = (detector_info.l2(middle) + detector_info.l2(middle+1)) / 2.

        l2_tof_equator_spectro = (l2_equator / v_fixed) * 1E+6  # in micro seconds

        return l2_tof_equator_spectro, l2_equator

    @staticmethod
    def _t0_offset(center_chopper_speed, center_chopper_phase, shifted_chopper_phase, center_psd_delay, shifted_psd_delay):
        """
        Calculates the t0 offset between measurements with and without inelastic offset.
        """
        return - (shifted_chopper_phase - center_chopper_phase) / center_chopper_speed / 6 + (shifted_psd_delay - center_psd_delay) * 1E-6

    def _set_parameters_on_instrument(self):
        """
        Set the parameters from the correct parameter file
        """
        idf_directory = config['instrumentDefinition.directory']
        ipf_name = self.instrument_name + '_' + self.analyser + '_' + self.reflection + '_Parameters.xml'
        parameter_file = os.path.join(idf_directory, ipf_name)

        LoadParameterFile(Workspace=self.instrument_ws, FileName=parameter_file)

    def _convert_to_tof_bats(self, ws):
        """
        Converts the X axis to TOF
        @param ws the input workspace
        """
        run = ws.getRun()
        det_info = ws.detectorInfo()

        peak_centre_channel = self.epp.cell("PeakCentre", self.epp.rowCount() - 1)
        channel_width = run.getLogData('PSD.time_of_flight_0').value

        v_fixed = self.instrument_ws.getInstrument().getNumberParameter('Vfixed')[0]

        # TODO check if the empty instrument is necessarily the correct one
        l2_elastic_tof_spectro, l2_equator_spectro = self._find_spectrometer_t0(v_fixed)

        # we use the l2 of the middle of each detector, as an approximation
        middle_pixel = NUMBER_OF_PIXEL_PER_DIFF_TUBE // 2
        l2_centre_diffractometer = (det_info.l2(middle_pixel) + det_info.l2(middle_pixel + 1)) / 2
        l2_elastic_tof_diffractometer = l2_elastic_tof_spectro * (l2_centre_diffractometer / l2_equator_spectro)

        l1 = det_info.l1()

        # we find the t0 offset to add to the total tof
        center_chopper_speed = self.epp.cell('ChopperSpeed', 0)
        center_chopper_phase = self.epp.cell('ChopperPhase', 0)
        center_psd_delay = self.epp.cell('PSD_TOF_Delay', 0)

        shifted_chopper_phase = self._get_pulse_chopper_info(run)[1]
        shifted_psd_delay = run.getLogData('PSD.time_of_flight_2').value
        t0_offset = self._t0_offset(center_chopper_speed, center_chopper_phase,
                                    shifted_chopper_phase, center_psd_delay, shifted_psd_delay)

        use_precise = False
        if use_precise:
            # take into account the fact that the detector is composed of strait tubes, and do not form a perfect circle
            # this correction is very slim and creates a ragged workspace, so probably not useful
            x = ws.extractX()
            for pixel in range(ws.getNumberHistograms()):
                if not det_info.isMonitor(pixel):
                    l2_pixel = det_info.l2(pixel)
                    elastic_tof_pixel = l2_pixel + (l1 / v_fixed + t0_offset) * 1E6
                    x_new = elastic_tof_pixel + (x[pixel] - peak_centre_channel) * channel_width
                    ws.setX(pixel, x_new)
            ws.getAxis(0).setUnit('TOF')

        else:
            tof_diffractometer = l2_elastic_tof_diffractometer + (l1 / v_fixed + t0_offset) * 1E6
            formula = '{0} + (x - {1})*{2}'.format(tof_diffractometer, peak_centre_channel, channel_width)

            ConvertAxisByFormula(InputWorkspace=ws, Axis='X', AxisUnits='TOF', Formula=formula, OutputWorkspace=ws)

    def _convert_to_final_units(self, ws):
        """
        Convert the workspace to wavelength and two theta units.
        @param ws the input workspace
        """
        efixed = self.instrument_ws.getInstrument().getNumberParameter('Efixed')[0]
        ConvertUnits(InputWorkspace=ws, OutputWorkspace=ws, Target='MomentumTransfer', EFixed=efixed)

    def _treat_doppler(self, ws):
        """
            Reduce Doppler diffraction data from the workspace.
            @param ws: the input workspace
        """
        if len(self.runs) > 1:
            number_of_channels = mtd[mtd[ws].getNames()[0]].blocksize()
            run = mtd[mtd[ws].getNames()[0]].getRun()
        else:
            number_of_channels = mtd[ws].blocksize()
            run = mtd[ws].getRun()

        if run.hasProperty('Doppler.incident_energy'):
            energy = run.getLogData('Doppler.incident_energy').value / 1000
        else:
            raise RuntimeError("Unable to find incident energy for Doppler mode")

        Rebin(InputWorkspace=ws, OutputWorkspace=self.output, Params=[0, number_of_channels, number_of_channels])
        self._normalize_by_monitor(self.output)

        ConvertSpectrumAxis(InputWorkspace=self.output,
                            OutputWorkspace=self.output,
                            Target='ElasticQ',
                            EMode="Direct",
                            EFixed=energy)

        ConvertToPointData(InputWorkspace=self.output, OutputWorkspace=self.output)

        ConjoinXRuns(InputWorkspaces=self.output,
                     SampleLogAsXAxis=self.scan_parameter,
                     FailBehaviour="Stop",
                     OutputWorkspace=self.output)

        ExtractUnmaskedSpectra(InputWorkspace=self.output, OutputWorkspace=self.output)

        Transpose(InputWorkspace=self.output, OutputWorkspace=self.output)

    def _treat_BATS(self, ws_name):
        """
        Reduces BATS diffraction data.
        @param ws_name the name of the workspace containing the data
        """
        ws = mtd[ws_name]
        self.instrument_name = ws.getInstrument().getName()[:-1]

        # TODO find a better way to do that
        # it looks like the parameter file cannot be loaded in a different instrument or something like that
        # anyway loading it directly doesn't work so here is an ugly workaround
        self.instrument_ws = LoadEmptyInstrument(InstrumentName=self.instrument_name)
        self._set_parameters_on_instrument()

        self._convert_to_tof_bats(ws)

        self._convert_to_final_units(ws)

    def PyExec(self):
        self.setUp()
        LoadAndMerge(Filename=self.getPropertyValue('SampleRuns'), OutputWorkspace=self.output,
                     LoaderOptions={"LoadDetectors": "Diffractometer"}, startProgress=0, endProgress=0.4)

        if len(self.runs) > 1:
            run = mtd[mtd[self.output].getNames()[0]].getRun()
        else:
            run = mtd[self.output].getRun()

        if run.hasProperty('acquisition_mode') and run.getLogData('acquisition_mode').value == 1:
            self.mode = "BATS"
            self.log().information("Mode recognized as BATS.")
        else:
            self.mode = "Doppler"
            self.log().information("Mode recognized as Doppler.")

        self.progress.report(4, "Treating data")
        if self.mode == "Doppler":
            self._treat_doppler(self.output)
        elif self.mode == "BATS":
            self._treat_BATS(self.output)

        self.setProperty("OutputWorkspace", mtd[self.output])


AlgorithmFactory.subscribe(IndirectILLReductionDIFF)
