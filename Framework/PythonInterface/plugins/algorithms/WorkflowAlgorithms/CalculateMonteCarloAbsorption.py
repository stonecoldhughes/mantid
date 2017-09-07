from __future__ import (absolute_import, division, print_function)

from mantid.api import (DataProcessorAlgorithm, AlgorithmFactory, PropertyMode, MatrixWorkspaceProperty,
                        WorkspaceGroupProperty, Progress, mtd, SpectraAxis)
from mantid.kernel import (VisibleWhenProperty, PropertyCriterion, StringListValidator, IntBoundedValidator,
                           FloatBoundedValidator, Direction, logger, LogicOperator, config)

import math
import numpy as np
import os.path


class CalculateMonteCarloAbsorption(DataProcessorAlgorithm):
    # General variables
    _emode = None
    _efixed = None
    _general_kwargs = None
    _shape = None
    _height = None

    # Sample variables
    _sample_angle = None
    _sample_center = None
    _sample_chemical_formula = None
    _sample_density = None
    _sample_density_type = None
    _sample_inner_radius = None
    _sample_outer_radius = None
    _sample_radius = None
    _sample_thickness = None
    _sample_unit = None
    _sample_width = None
    _sample_ws = None

    # Container variables
    _container_angle = None
    _container_center = None
    _container_chemical_formula = None
    _container_density = None
    _container_density_type = None
    _container_inner_radius = None
    _container_outer_radius = None
    _container_thickness = None
    _container_width = None

    # Output workspaces
    _ass_ws = None
    _acc_ws = None
    _output_ws = None

    def category(self):
        return "Workflow\\Inelastic;CorrectionFunctions\\AbsorptionCorrections;Workflow\\MIDAS"

    def summary(self):
        return "Calculates indirect absorption corrections for a given sample shape."

    def PyInit(self):
        # Beam Options
        self.declareProperty(name='BeamHeight', defaultValue=1.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Height of the beam (cm)')
        self.declareProperty(name='BeamWidth', defaultValue=1.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Width of the beam (cm)')

        self.setPropertyGroup('BeamHeight', 'Beam Options')
        self.setPropertyGroup('BeamWidth', 'Beam Options')

        # Monte Carlo options
        self.declareProperty(name='NumberOfWavelengthPoints', defaultValue=10,
                             validator=IntBoundedValidator(1),
                             doc='Number of wavelengths for calculation')
        self.declareProperty(name='EventsPerPoint', defaultValue=1000,
                             validator=IntBoundedValidator(0),
                             doc='Number of neutron events')
        self.declareProperty(name='Interpolation', defaultValue='Linear',
                             validator=StringListValidator(
                                 ['Linear', 'CSpline']),
                             doc='Type of interpolation')

        self.setPropertyGroup('NumberOfWavelengthPoints', 'Monte Carlo Options')
        self.setPropertyGroup('EventsPerPoint', 'Monte Carlo Options')
        self.setPropertyGroup('Interpolation', 'Monte Carlo Options')

        # Sample options
        self.declareProperty(MatrixWorkspaceProperty('SampleWorkspace', '', direction=Direction.Input),
                             doc='Sample Workspace')
        self.declareProperty(name='SampleChemicalFormula', defaultValue='',
                             doc='Chemical formula for the sample material')
        self.declareProperty(name='SampleDensityType', defaultValue='Mass Density',
                             validator=StringListValidator(['Mass Density', 'Number Density']),
                             doc='Sample density type')
        self.declareProperty(name='SampleDensity', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Sample density')

        self.setPropertyGroup('SampleWorkspace', 'Sample Options')
        self.setPropertyGroup('SampleChemicalFormula', 'Sample Options')
        self.setPropertyGroup('SampleDensityType', 'Sample Options')
        self.setPropertyGroup('SampleDensity', 'Sample Options')

        # Container options
        self.declareProperty(MatrixWorkspaceProperty('ContainerWorkspace', '', direction=Direction.Input,
                                                     optional=PropertyMode.Optional),
                             doc='Container Workspace')

        container_condition = VisibleWhenProperty('ContainerWorkspace', PropertyCriterion.IsNotDefault)

        self.declareProperty(name='ContainerChemicalFormula', defaultValue='',
                             doc='Chemical formula for the container material')
        self.declareProperty(name='ContainerDensityType', defaultValue='Mass Density',
                             validator=StringListValidator(['Mass Density', 'Number Density']),
                             doc='Container density type')
        self.declareProperty(name='ContainerDensity', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Container density')

        self.setPropertyGroup('ContainerWorkspace', 'Container Options')
        self.setPropertyGroup('ContainerChemicalFormula', 'Container Options')
        self.setPropertyGroup('ContainerDensityType', 'Container Options')
        self.setPropertyGroup('ContainerDensity', 'Container Options')

        self.setPropertySettings('ContainerChemicalFormula', container_condition)
        self.setPropertySettings('ContainerDensityType', container_condition)
        self.setPropertySettings('ContainerDensity', container_condition)

        # Shape options
        self.declareProperty(name='Shape', defaultValue='FlatPlate',
                             validator=StringListValidator(['FlatPlate', 'Cylinder', 'Annulus']),
                             doc='Geometric shape of the sample environment')

        flat_plate_condition = VisibleWhenProperty('Shape', PropertyCriterion.IsEqualTo, 'FlatPlate')
        cylinder_condition = VisibleWhenProperty('Shape', PropertyCriterion.IsEqualTo, 'Cylinder')
        annulus_condition = VisibleWhenProperty('Shape', PropertyCriterion.IsEqualTo, 'Annulus')

        # height is common to all, and should be the same for sample and container
        self.declareProperty('Height', defaultValue=0.0, validator=FloatBoundedValidator(0.0),
                             doc='Height of the sample environment (cm)')

        self.setPropertyGroup('Shape', 'Shape Options')
        self.setPropertyGroup('Height', 'Shape Options')

        # ---------------------------Sample---------------------------
        # Flat Plate
        self.declareProperty(name='SampleWidth', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Width of the sample environment (cm)')
        self.declareProperty(name='SampleThickness', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Thickness of the sample environment (cm)')
        self.declareProperty(name='SampleCenter', defaultValue=0.0,
                             doc='Center of the sample environment')
        self.declareProperty(name='SampleAngle', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Angle of the sample environment with respect to the beam (degrees)')

        self.setPropertySettings('SampleWidth', flat_plate_condition)
        self.setPropertySettings('SampleThickness', flat_plate_condition)
        self.setPropertySettings('SampleCenter', flat_plate_condition)
        self.setPropertySettings('SampleAngle', flat_plate_condition)

        self.setPropertyGroup('SampleWidth', 'Sample Shape Options')
        self.setPropertyGroup('SampleThickness', 'Sample Shape Options')
        self.setPropertyGroup('SampleCenter', 'Sample Shape Options')
        self.setPropertyGroup('SampleAngle', 'Sample Shape Options')

        # Cylinder
        self.declareProperty(name='SampleRadius', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Radius of the sample environment (cm)')

        self.setPropertySettings('SampleRadius', cylinder_condition)
        self.setPropertyGroup('SampleRadius', 'Sample Shape Options')

        # Annulus
        self.declareProperty(name='SampleInnerRadius', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Inner radius of the sample environment (cm)')
        self.declareProperty(name='SampleOuterRadius', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Outer radius of the sample environment (cm)')

        self.setPropertySettings('SampleInnerRadius', annulus_condition)
        self.setPropertySettings('SampleOuterRadius', annulus_condition)

        self.setPropertyGroup('SampleInnerRadius', 'Sample Shape Options')
        self.setPropertyGroup('SampleOuterRadius', 'Sample Shape Options')

        # ---------------------------Container---------------------------
        # Flat Plate
        self.declareProperty(name='ContainerFrontThickness', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Front thickness of the container environment (cm)')
        self.declareProperty(name='ContainerBackThickness', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Back thickness of the container environment (cm)')

        container_flat_plate_condition = VisibleWhenProperty(container_condition, flat_plate_condition,
                                                             LogicOperator.And)

        self.setPropertySettings('ContainerFrontThickness', container_flat_plate_condition)
        self.setPropertySettings('ContainerBackThickness', container_flat_plate_condition)

        self.setPropertyGroup('ContainerFrontThickness', 'Container Shape Options')
        self.setPropertyGroup('ContainerBackThickness', 'Container Shape Options')

        # Both cylinder and annulus have an annulus container

        not_flat_plate_condition = VisibleWhenProperty('Shape', PropertyCriterion.IsNotEqualTo, 'FlatPlate')

        container_n_f_p_condition = VisibleWhenProperty(container_condition, not_flat_plate_condition,
                                                        LogicOperator.And)

        self.declareProperty(name='ContainerInnerRadius', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Inner radius of the container environment (cm)')
        self.declareProperty(name='ContainerOuterRadius', defaultValue=0.0,
                             validator=FloatBoundedValidator(0.0),
                             doc='Outer radius of the container environment (cm)')

        self.setPropertySettings('ContainerInnerRadius', container_n_f_p_condition)
        self.setPropertySettings('ContainerOuterRadius', container_n_f_p_condition)

        self.setPropertyGroup('ContainerInnerRadius', 'Container Shape Options')
        self.setPropertyGroup('ContainerOuterRadius', 'Container Shape Options')

        # output
        self.declareProperty(WorkspaceGroupProperty(name='CorrectionsWorkspace',
                                                    defaultValue='corrections',
                                                    direction=Direction.Output,
                                                    optional=PropertyMode.Optional),
                             doc='Name of the workspace group to save correction factors')
        self.setPropertyGroup('CorrectionsWorkspace', 'Output Options')

    def PyExec(self):

        # set up progress reporting
        prog = Progress(self, 0, 1, 10)

        prog.report('Converting to wavelength')
        sample_wave_ws = self._convert_to_wavelength(self._sample_ws)

        prog.report('Calculating sample absorption factors')

        sample_kwargs = dict()
        sample_kwargs.update(self._general_kwargs)
        sample_kwargs['ChemicalFormula'] = self._sample_chemical_formula
        sample_kwargs['DensityType'] = self._sample_density_type
        sample_kwargs['Density'] = self._sample_density
        sample_kwargs['Height'] = self._height
        sample_kwargs['Shape'] = self._shape

        if self._shape == 'FlatPlate':
            sample_kwargs['Width'] = self._sample_width
            sample_kwargs['Thickness'] = self._sample_thickness
            sample_kwargs['Angle'] = self._sample_angle
            sample_kwargs['Center'] = self._sample_center

        if self._shape == 'Cylinder':
            sample_kwargs['Radius'] = self._sample_radius

        if self._shape == 'Annulus':
            sample_kwargs['InnerRadius'] = self._sample_inner_radius
            sample_kwargs['OuterRadius'] = self._sample_outer_radius

        ss_monte_carlo_alg = self.createChildAlgorithm("SimpleShapeMonteCarloAbsorption", enableLogging=True)
        ss_monte_carlo_alg.setProperty("InputWorkspace", sample_wave_ws)
        self._set_algorithm_properties(ss_monte_carlo_alg, sample_kwargs)
        ss_monte_carlo_alg.execute()
        ass_ws = ss_monte_carlo_alg.getProperty("OutputWorkspace").value

        sample_log_names = []
        sample_log_values = []

        for log_name, log_value in sample_kwargs.items():
            sample_log_names.append("sample_" + log_name.lower())
            sample_log_values.append(log_value)

        ass_ws = self._convert_from_wavelength(ass_ws)
        self._add_sample_log_multiple(ass_ws, sample_log_names, sample_log_values)

        if not self.isChild():
            mtd.addOrReplace(self._ass_ws_name, ass_ws)

        if self._container_ws:
            prog.report('Calculating container absorption factors')

            container_wave_1 = self._convert_to_wavelength(self._container_ws)
            container_wave_2 = self._clone_ws(container_wave_1)

            container_kwargs = dict()
            container_kwargs.update(self._general_kwargs)
            container_kwargs['ChemicalFormula'] = self._container_chemical_formula
            container_kwargs['DensityType'] = self._container_density_type
            container_kwargs['Density'] = self._container_density
            container_kwargs['Height'] = self._height
            container_kwargs['Shape'] = self._shape
            self._set_algorithm_properties(ss_monte_carlo_alg, container_kwargs)

            if self._shape == 'FlatPlate':
                offset_front = 0.5 * (self._container_front_thickness + self._sample_thickness)
                ss_monte_carlo_alg.setProperty("InputWorkspace", container_wave_1)
                ss_monte_carlo_alg.setProperty("Width", self._sample_width)
                ss_monte_carlo_alg.setProperty("Angle", self._sample_angle)
                ss_monte_carlo_alg.setProperty("Thickness", self._container_front_thickness)
                ss_monte_carlo_alg.setProperty("Center", -offset_front)
                ss_monte_carlo_alg.execute()
                acc_1 = ss_monte_carlo_alg.getProperty("OutputWorkspace").value

                offset_back = 0.5 * (self._container_back_thickness + self._sample_thickness)
                ss_monte_carlo_alg.setProperty("InputWorkspace", container_wave_2)
                ss_monte_carlo_alg.setProperty("Thickness", self._container_back_thickness)
                ss_monte_carlo_alg.setProperty("Center", offset_back)
                ss_monte_carlo_alg.execute()
                acc_2 = ss_monte_carlo_alg.getProperty("OutputWorkspace").value

                acc_ws = self._multiply(acc_1, acc_2)

            elif self._shape == 'Cylinder':
                ss_monte_carlo_alg.setProperty("InputWorkspace", container_wave_1)
                ss_monte_carlo_alg.setProperty("InnerRadius", self._container_inner_radius)
                ss_monte_carlo_alg.setProperty("OuterRadius", self._container_outer_radius)
                ss_monte_carlo_alg.setProperty("Shape", "Annulus")
                ss_monte_carlo_alg.execute()
                acc_ws = ss_monte_carlo_alg.getProperty("OutputWorkspace").value

            elif self._shape == 'Annulus':
                ss_monte_carlo_alg.setProperty("InputWorkspace", container_wave_1)
                ss_monte_carlo_alg.setProperty("InnerRadius", self._container_inner_radius)
                ss_monte_carlo_alg.setProperty("OuterRadius", self._container_outer_radius)
                ss_monte_carlo_alg.execute()
                acc_1 = ss_monte_carlo_alg.getProperty("OutputWorkspace").value

                ss_monte_carlo_alg.setProperty("InputWorkspace", container_wave_2)
                ss_monte_carlo_alg.execute()
                acc_2 = ss_monte_carlo_alg.getProperty("OutputWorkspace").value

                acc_ws = self._multiply(acc_1, acc_2)

            for log_name, log_value in container_kwargs.items():
                sample_log_names.append("container_" + log_name.lower())
                sample_log_values.append(log_value)

            acc_ws = self._convert_from_wavelength(acc_ws)

            self._add_sample_log_multiple(acc_ws, sample_log_names, sample_log_values)

            if not self.isChild():
                mtd.addOrReplace(self._acc_ws_name, acc_ws)

            self._output_ws = self._group_ws([ass_ws, acc_ws])
        else:
            self._output_ws = self._group_ws([ass_ws])

        self.setProperty('CorrectionsWorkspace', self._output_ws)

    def _setup(self):

        # The beam properties and monte carlo properties are simply passed straight on to the
        # SimpleShapeMonteCarloAbsorptionCorrection algorithm so they are being put into
        # a dictionary for simplicity

        self._general_kwargs = {'BeamHeight': self.getProperty('BeamHeight').value,
                                'BeamWidth': self.getProperty('BeamWidth').value,
                                'NumberOfWavelengthPoints': self.getProperty('NumberOfWavelengthPoints').value,
                                'EventsPerPoint': self.getProperty('EventsPerPoint').value,
                                'Interpolation': self.getProperty('Interpolation').value}

        self._sample_ws = self.getProperty("SampleWorkspace").value
        self._container_ws = self.getProperty('ContainerWorkspace').value
        self._shape = self.getProperty('Shape').value
        self._height = self.getProperty('Height').value

        self._sample_unit = self._sample_ws.getAxis(0).getUnit().unitID()
        logger.information('Input X-unit is {}'.format(self._sample_unit))
        if self._sample_unit == 'dSpacing':
            self._emode = 'Elastic'
        else:
            self._emode = str(self._sample_ws.getEMode())
        if self._emode == 'Indirect' or 'Direct':
            self._efixed = self._get_efixed()

        self._sample_chemical_formula = self.getPropertyValue('SampleChemicalFormula')
        self._sample_density_type = self.getPropertyValue('SampleDensityType')
        self._sample_density = self.getProperty('SampleDensity').value

        if self._container_ws:
            self._container_chemical_formula = self.getPropertyValue('ContainerChemicalFormula')
            self._container_density_type = self.getPropertyValue('ContainerDensityType')
            self._container_density = self.getProperty('ContainerDensity').value

        if self._shape == 'FlatPlate':
            self._sample_width = self.getProperty('SampleWidth').value
            self._sample_thickness = self.getProperty('SampleThickness').value
            self._sample_angle = self.getProperty('SampleAngle').value
            self._sample_center = self.getProperty('SampleCenter').value

        if self._shape == 'Cylinder':
            self._sample_radius = self.getProperty('SampleRadius').value

        if self._shape == 'Annulus':
            self._sample_inner_radius = self.getProperty('SampleInnerRadius').value
            self._sample_outer_radius = self.getProperty('SampleOuterRadius').value

        if self._container_ws:
            if self._shape == 'FlatPlate':
                self._container_front_thickness = self.getProperty('ContainerFrontThickness').value
                self._container_back_thickness = self.getProperty('ContainerBackThickness').value

            else:
                self._container_inner_radius = self.getProperty('ContainerInnerRadius').value
                self._container_outer_radius = self.getProperty('ContainerOuterRadius').value

        self._output_ws = self.getProperty('CorrectionsWorkspace').value
        output_ws_name = self.getPropertyValue('CorrectionsWorkspace')
        self._ass_ws_name = output_ws_name + "_ass"
        self._acc_ws_name = output_ws_name + "_acc"
        self._indirect_q_axis = None

    def validateInputs(self):
        issues = dict()

        try:
            self._setup()
        except Exception as err:
            issues['SampleWorkspace'] = str(err)

        if self._shape == 'Annulus':
            if self._sample_inner_radius >= self._sample_outer_radius:
                issues['SampleOuterRadius'] = 'Must be greater than SampleInnerRadius'

        if self._container_ws:
            container_unit = self._container_ws.getAxis(0).getUnit().unitID()
            if container_unit != self._sample_unit:
                raise ValueError('Sample and Container units must be the same!')

            if self._shape == 'Cylinder':
                if self._container_inner_radius <= self._sample_radius:
                    issues['ContainerInnerRadius'] = 'Must be greater than SampleRadius'
                if self._container_outer_radius <= self._container_inner_radius:
                    issues['ContainerOuterRadius'] = 'Must be greater than ContainerInnerRadius'

            if self._shape == 'Annulus':
                if self._container_inner_radius >= self._sample_inner_radius:
                    issues['ContainerInnerRadius'] = 'Must be less than SampleInnerRadius'
                if self._container_outer_radius <= self._sample_outer_radius:
                    issues['ContainerOuterRadius'] = 'Must be greater than SampleOuterRadius'

        return issues

    def _get_efixed(self):
        """
        Returns the efixed value relating to the specified workspace
        """
        inst = self._sample_ws.getInstrument()

        if inst.hasParameter('Efixed'):
            return inst.getNumberParameter('Efixed')[0]

        if inst.hasParameter('analyser'):
            analyser_comp = inst.getComponentByName(inst.getStringParameter('analyser')[0])

            if analyser_comp is not None and analyser_comp.hasParameter('Efixed'):
                return analyser_comp.getNumberParameter('EFixed')[0]

        raise ValueError('No Efixed parameter found')

    # ------------------------------- Converting to/from wavelength -------------------------------

    def _convert_to_wavelength(self, workspace):

        if self._sample_unit == 'Wavelength':
            return self._clone_ws(workspace)
        else:
            convert_unit_alg = self.createChildAlgorithm("ConvertUnits", enableLogging=True)

            if self._emode == 'Indirect':
                x_unit = workspace.getAxis(0).getUnit().unitID()
                y_unit = workspace.getAxis(1).getUnit().unitID()

                # Check whether to create wavelength workspace for Indirect Elastic
                if (x_unit == 'MomentumTransfer' and not y_unit == 'EnergyTransfer') \
                        or (y_unit == 'MomentumTransfer' and not x_unit == 'EnergyTransfer'):
                    self._indirect_q_axis = 'Y'

                    if x_unit == 'MomentumTransfer':
                        self._indirect_q_axis = 'X'
                        logger.information('X-Axis of the input workspace is Q')
                        transpose_alg = self.createChildAlgorithm("Transpose", enableLogging=False)
                        transpose_alg.setProperty("InputWorkspace", workspace)
                        transpose_alg.execute()
                        workspace = transpose_alg.getProperty("OutputWorkspace").value
                    return self._create_waves_indirect_elastic(workspace)
                else:
                    convert_unit_alg.setProperty("EFixed", self._efixed)

            convert_unit_alg.setProperty("InputWorkspace", workspace)
            convert_unit_alg.setProperty("Target", 'Wavelength')
            convert_unit_alg.setProperty("EMode", self._emode)

            convert_unit_alg.execute()

            return convert_unit_alg.getProperty("OutputWorkspace").value

    def _convert_from_wavelength(self, workspace):

        convert_unit_alg = self.createChildAlgorithm("ConvertUnits", enableLogging=False)
        convert_unit_alg.setProperty("Target", self._sample_unit)

        if self._sample_unit != 'Wavelength':

            if self._emode == 'Indirect':

                if self._indirect_q_axis is not None:

                    if self._indirect_q_axis == 'X':
                        transpose_alg = self.createChildAlgorithm("Transpose", enableLogging=False)
                        transpose_alg.setProperty("InputWorkspace", workspace)
                        transpose_alg.execute()
                        workspace = transpose_alg.getProperty("OutputWorkspace").value
                        workspace.setX(0, self._q_values)
                        workspace.getAxis(0).setUnit("MomentumTransfer")
                        return workspace
                    convert_unit_alg.setProperty("Target", "MomentumTransfer")
                convert_unit_alg.setProperty("EFixed", self._efixed)

            convert_unit_alg.setProperty("InputWorkspace", workspace)
            convert_unit_alg.setProperty("EMode", self._emode)
            convert_unit_alg.execute()
            return convert_unit_alg.getProperty("OutputWorkspace").value

        else:
            return workspace

    # ------------------------------- Converting IndirectElastic to wavelength ------------------------------

    def _create_waves_indirect_elastic(self, workspace):
        """
        Creates a wavelength workspace, from the workspace with the specified input workspace
        name, using an Elastic instrument definition file. E-Mode must be Indirect and the y-axis
        of the input workspace must be in units of Q.

        :param workspace:   The input workspace.
        :return:            The output wavelength workspace.
        """
        self._q_values = workspace.getAxis(1).extractValues()

        # ---------- Load Elastic Instrument Definition File ----------

        idf_name = workspace.getInstrument().getName() + '_Definition_elastic.xml'

        idf_path = os.path.join(config.getInstrumentDirectory(), idf_name)
        logger.information('IDF = %s' % idf_path)

        load_alg = self.createChildAlgorithm("LoadInstrument", enableLogging=True)
        load_alg.setProperty("Workspace", workspace)
        load_alg.setProperty("Filename", idf_path)
        load_alg.setProperty("RewriteSpectraMap", True)
        load_alg.execute()

        # Replace y-axis with spectra axis
        workspace.replaceAxis(1, SpectraAxis.create(workspace))
        e_fixed = float(self._efixed)
        logger.information('Efixed = %f' % e_fixed)

        # ---------- Set Instrument Parameters ----------

        sip_alg = self.createChildAlgorithm("SetInstrumentParameter", enableLogging=False)
        sip_alg.setProperty("Workspace", workspace)
        sip_alg.setProperty("ParameterName", 'EFixed')
        sip_alg.setProperty("ParameterType", 'Number')
        sip_alg.setProperty("Value", str(e_fixed))
        sip_alg.execute()

        # ---------- Calculate Wavelength ----------

        wave = math.sqrt(81.787 / e_fixed)
        logger.information('Wavelength = %f' % wave)
        workspace.getAxis(0).setUnit('Wavelength')

        # ---------- Format Input Workspace ---------

        convert_alg = self.createChildAlgorithm("ConvertToHistogram", enableLogging=False)
        convert_alg.setProperty("InputWorkspace", workspace)
        convert_alg.execute()

        workspace = self._crop_ws(convert_alg.getProperty("OutputWorkspace").value)

        # --------- Set wavelengths as X-values in Output Workspace ----------

        waves = (0.01 * np.arange(-1, workspace.blocksize())) + wave
        logger.information('Waves : ' + str(waves))
        nhist = workspace.getNumberHistograms()
        for idx in range(nhist):
            workspace.setX(idx, waves)
        self._change_angles(workspace, self._q_values, wave)

        return workspace

    def _change_angles(self, workspace, q_values, wave):
        work_dir = config['defaultsave.directory']
        k0 = 4.0 * math.pi / wave
        theta = 2.0 * np.degrees(np.arcsin(q_values / k0))  # convert to angle

        filename = 'Elastic_angles.txt'
        path = os.path.join(work_dir, filename)
        logger.information('Creating angles file : ' + path)
        handle = open(path, 'w')
        head = 'spectrum,theta'
        handle.write(head + " \n")
        for n in range(0, len(theta)):
            handle.write(str(n + 1) + '   ' + str(theta[n]) + "\n")
        handle.close()

        update_alg = self.createChildAlgorithm("UpdateInstrumentFromFile", enableLogging=False)
        update_alg.setProperty("Workspace", workspace)
        update_alg.setProperty("Filename", path)
        update_alg.setProperty("MoveMonitors", False)
        update_alg.setProperty("IgnorePhi", True)
        update_alg.setProperty("AsciiHeader", head)
        update_alg.setProperty("SkipFirstNLines", 1)

    def _crop_ws(self, workspace):
        x = workspace.dataX(0)
        xmin = x[0]
        xmax = x[1]
        crop_alg = self.createChildAlgorithm("CropWorkspace", enableLogging=False)
        crop_alg.setProperty("InputWorkspace", workspace)
        crop_alg.setProperty("XMin", xmin)
        crop_alg.setProperty("XMax", xmax)
        crop_alg.execute()
        return crop_alg.getProperty("OutputWorkspace").value

    # ------------------------------- Child algorithms -------------------------------

    def _clone_ws(self, input_ws):
        clone_alg = self.createChildAlgorithm("CloneWorkspace", enableLogging=False)
        clone_alg.setProperty("InputWorkspace", input_ws)
        clone_alg.execute()
        return clone_alg.getProperty("OutputWorkspace").value

    def _multiply(self, lhs_ws, rhs_ws):
        multiply_alg = self.createChildAlgorithm("Multiply", enableLogging=False)
        multiply_alg.setProperty("LHSWorkspace", lhs_ws)
        multiply_alg.setProperty("RHSWorkspace", rhs_ws)
        multiply_alg.execute()
        return multiply_alg.getProperty('OutputWorkspace').value

    def _group_ws(self, input_ws):
        group_alg = self.createChildAlgorithm("GroupWorkspaces", enableLogging=False)
        group_alg.setProperty("InputWorkspaces", input_ws)
        group_alg.execute()
        return group_alg.getProperty("OutputWorkspace").value

    def _add_sample_log_multiple(self, input_ws, log_names, log_values):
        sample_log_mult_alg = self.createChildAlgorithm("AddSampleLogMultiple", enableLogging=False)
        sample_log_mult_alg.setProperty("Workspace", input_ws)
        sample_log_mult_alg.setProperty("LogNames", log_names)
        sample_log_mult_alg.setProperty("LogValues", log_values)
        sample_log_mult_alg.execute()

    # ------------------------------- Utility algorithms -------------------------------
    def _set_algorithm_properties(self, algorithm, properties):

        for key, value in properties.items():
            algorithm.setProperty(key, value)


# Register algorithm with Mantid
AlgorithmFactory.subscribe(CalculateMonteCarloAbsorption)
