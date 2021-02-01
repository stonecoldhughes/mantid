# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
import unittest
from os import path
from unittest import mock
from unittest.mock import MagicMock
from mantid.simpleapi import Load, Fit
from mantidqt.utils.qt.testing import start_qapplication
from Engineering.gui.engineering_diffraction.engineering_diffraction import EngineeringDiffractionGui
from Engineering.gui.engineering_diffraction.presenter import EngineeringDiffractionPresenter
from Engineering.gui.engineering_diffraction.engineering_diffraction_io import EngineeringDiffractionDecoder, \
    EngineeringDiffractionEncoder
from Engineering.gui.engineering_diffraction.tabs.calibration.model import CalibrationModel
from Engineering.gui.engineering_diffraction.tabs.calibration.view import CalibrationView
from Engineering.gui.engineering_diffraction.tabs.calibration.presenter import CalibrationPresenter
from Engineering.gui.engineering_diffraction.tabs.focus.model import FocusModel
from Engineering.gui.engineering_diffraction.tabs.focus.view import FocusView
from Engineering.gui.engineering_diffraction.tabs.focus.presenter import FocusPresenter
from Engineering.gui.engineering_diffraction.tabs.fitting.view import FittingView
from Engineering.gui.engineering_diffraction.tabs.fitting.presenter import FittingPresenter
from Engineering.gui.engineering_diffraction.tabs.fitting.plotting.plot_view import FittingPlotView
from Engineering.gui.engineering_diffraction.tabs.fitting.plotting.EngDiff_fitpropertybrowser import \
    EngDiffFitPropertyBrowser
from Engineering.gui.engineering_diffraction.settings.settings_model import SettingsModel
from Engineering.gui.engineering_diffraction.settings.settings_view import SettingsView
from Engineering.gui.engineering_diffraction.settings.settings_presenter import SettingsPresenter

IO_VERSION = 1
TEST_FILE = "ENGINX_277208_focused_bank_2.nxs"
TEST_WS = 'ENGINX_277208_focused_bank_2_TOF'
FIT_WS = TEST_WS + '_Workspace'
FIT_DICT = {'properties': {'InputWorkspace': TEST_WS, 'Output': TEST_WS, 'StartX':
            5731.386819290339, 'EndX': 52554.79335660165, 'Function': 'name=Gaussian,Height=0.0365604,PeakCentre=37490.'
                                                                      '4,Sigma=1284.55;name=Gaussian,Height=0.0190721,P'
                                                                      'eakCentre=21506.1,Sigma=1945.78',
            'ConvolveMembers': True, 'OutputCompositeMembers': True}}

SETTINGS_DICT = {
    "full_calibration": "",
    "save_location": path.join(path.expanduser("~"), "Engineering_Mantid"),
    "recalc_vanadium": False,
    "logs": ','.join(
        ['Temp_1', 'W_position', 'X_position', 'Y_position', 'Z_position', 'stress', 'strain', 'stressrig_go']),
    "primary_log": 'strain',
    "sort_ascending": False  # this is changed to false to show a deviation from the default
}

ENCODED_DICT = {'encoder_version': IO_VERSION, 'current_tab': 2, 'data_loaded_workspaces':
                [TEST_WS], 'plotted_workspaces': [FIT_WS], 'fit_properties': FIT_DICT, 'plot_diff': 'True',
                'settings_dict': SETTINGS_DICT, 'background_params': {}}


def _create_fit_workspace():
    fn_input = FIT_DICT['properties']
    Fit(**fn_input)


def _load_test_file():
    Load(TEST_FILE, OutputWorkspace=TEST_WS)


class EngineeringDiffractionEncoderTest(unittest.TestCase):

    def setUp(self):
        self.fitprop_browser = None
        self.mock_view = mock.create_autospec(EngineeringDiffractionGui)
        self.presenter = EngineeringDiffractionPresenter()
        self.create_test_calibration_presenter()
        self.create_test_focus_presenter()
        self.create_test_fitting_presenter()
        self.create_test_settings_presenter()
        self.mock_view.presenter = self.presenter
        self.mock_tabs = MagicMock()
        self.mock_view.tabs = self.mock_tabs
        self.mock_tabs.currentIndex.return_value = 0
        self.encoder = EngineeringDiffractionEncoder()
        self.decoder = EngineeringDiffractionDecoder()
        self.io_version = 1
        self.fit_ws = None

    def create_test_focus_presenter(self):
        focus_model = FocusModel()
        focus_view = mock.create_autospec(FocusView)
        self.presenter.focus_presenter = FocusPresenter(focus_model, focus_view)

    def create_test_calibration_presenter(self):
        cal_model = CalibrationModel()
        cal_view = mock.create_autospec(CalibrationView)
        self.presenter.calibration_presenter = CalibrationPresenter(cal_model, cal_view)

    def create_test_fitting_presenter(self):
        fitting_view = mock.create_autospec(FittingView)
        self.presenter.fitting_presenter = FittingPresenter(fitting_view)
        self.presenter.focus_presenter.add_focus_subscriber(self.presenter.fitting_presenter.data_widget.presenter.
                                                            focus_run_observer)
        fitting_plot_view = mock.create_autospec(FittingPlotView)
        self.fitprop_browser = mock.create_autospec(EngDiffFitPropertyBrowser)
        fitting_plot_view.fit_browser = self.fitprop_browser
        self.presenter.fitting_presenter.plot_widget.view = fitting_plot_view

    def create_test_settings_presenter(self):
        settings_model = SettingsModel()
        settings_view = mock.create_autospec(SettingsView)
        settings_presenter = SettingsPresenter(settings_model, settings_view)
        self.presenter.settings_presenter = settings_presenter
        settings_model.set_settings_dict(SETTINGS_DICT)

    def test_blank_gui_encodes(self):
        self.mock_tabs.currentIndex.return_value = 0
        test_dic = self.encoder.encode(self.mock_view)
        self.assertEqual({'encoder_version': self.io_version, 'current_tab': 0, 'settings_dict': SETTINGS_DICT},
                         test_dic)

    def test_loaded_workspaces_encode(self):
        self.presenter.fitting_presenter.data_widget.presenter.model.load_files(TEST_FILE, 'TOF')
        self.fitprop_browser.read_current_fitprop.return_value = None
        test_dic = self.encoder.encode(self.mock_view)
        self.assertEqual({'encoder_version': self.io_version, 'current_tab': 0, 'data_loaded_workspaces':
                         [TEST_WS], 'plotted_workspaces': [], 'fit_properties': None, 'settings_dict':
                         SETTINGS_DICT, 'background_params': {}}, test_dic)

    def test_fits_encode(self):
        self.presenter.fitting_presenter.data_widget.presenter.model.load_files(TEST_FILE, 'TOF')
        self.fitprop_browser.read_current_fitprop.return_value = FIT_DICT
        self.fitprop_browser.plotDiff.return_value = True
        self.presenter.fitting_presenter.data_widget.presenter.plotted = {FIT_WS}
        test_dic = self.encoder.encode(self.mock_view)
        self.assertEqual({'encoder_version': self.io_version, 'current_tab': 0, 'data_loaded_workspaces':
                          [TEST_WS], 'plotted_workspaces': [FIT_WS], 'fit_properties': FIT_DICT, 'plot_diff':
                          'True', 'settings_dict': SETTINGS_DICT, 'background_params': {}}, test_dic)


@start_qapplication
class EngineeringDiffractionDecoderTest(unittest.TestCase):

    def setUp(self):
        # ConfigService.setLogLevel(7)
        self.encoder = EngineeringDiffractionEncoder()
        self.decoder = EngineeringDiffractionDecoder()
        _load_test_file()
        _create_fit_workspace()

    def test_decode_produces_gui_returning_same_dict(self):
        self.gui = self.decoder.decode(ENCODED_DICT)
        post_decode_dict = self.encoder.encode(self.gui)
        self.assertEqual(ENCODED_DICT, post_decode_dict)


if __name__ == '__main__':
    unittest.main()
