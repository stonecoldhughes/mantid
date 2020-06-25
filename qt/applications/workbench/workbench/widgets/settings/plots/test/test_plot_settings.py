# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
#  This file is part of the mantid workbench
import unittest

from unittest.mock import call, patch
from mantidqt.utils.qt.testing import start_qapplication
from mantidqt.utils.testing.strict_mock import StrictMock
from workbench.widgets.settings.plots.presenter import PlotSettings

from qtpy.QtCore import Qt


class MockConfigService(object):
    def __init__(self):
        self.getString = StrictMock(return_value="1")
        self.setString = StrictMock()


@start_qapplication
class PlotsSettingsTest(unittest.TestCase):
    CONFIG_SERVICE_CLASSPATH = "workbench.widgets.settings.plots.presenter.ConfigService"

    def assert_connected_once(self, owner, signal):
        self.assertEqual(1, owner.receivers(signal))

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_load_current_setting_values(self, mock_ConfigService):
        # load current setting is called automatically in the constructor
        PlotSettings(None)

        mock_ConfigService.getString.assert_has_calls([call(PlotSettings.NORMALIZATION),
                                                       call(PlotSettings.SHOW_TITLE),
                                                       call(PlotSettings.X_AXES_SCALE),
                                                       call(PlotSettings.Y_AXES_SCALE),
                                                       call(PlotSettings.LINE_STYLE),
                                                       call(PlotSettings.DRAW_STYLE),
                                                       call(PlotSettings.LINE_WIDTH),
                                                       call(PlotSettings.MARKER_STYLE),
                                                       call(PlotSettings.MARKER_SIZE),
                                                       call(PlotSettings.ERROR_WIDTH),
                                                       call(PlotSettings.CAPSIZE),
                                                       call(PlotSettings.CAP_THICKNESS),
                                                       call(PlotSettings.ERROR_EVERY),
                                                       call(PlotSettings.LEGEND_LOCATION),
                                                       call(PlotSettings.LEGEND_FONT_SIZE)])

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_normalization_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_normalization_changed(Qt.Checked)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.NORMALIZATION, "On")

        mock_ConfigService.setString.reset_mock()

        presenter.action_normalization_changed(Qt.Unchecked)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.NORMALIZATION, "Off")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_show_title_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_show_title_changed(Qt.Checked)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.SHOW_TITLE, "On")

        mock_ConfigService.setString.reset_mock()

        presenter.action_show_title_changed(Qt.Unchecked)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.SHOW_TITLE, "Off")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_default_x_axes_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_default_x_axes_changed("Linear")
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.X_AXES_SCALE, "Linear")

        mock_ConfigService.setString.reset_mock()

        presenter.action_default_x_axes_changed("Log")
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.X_AXES_SCALE, "Log")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_default_y_axes_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_default_y_axes_changed("Linear")
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.Y_AXES_SCALE, "Linear")

        mock_ConfigService.setString.reset_mock()

        presenter.action_default_y_axes_changed("Log")
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.Y_AXES_SCALE, "Log")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_line_style_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_line_style_changed("dashed")
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.LINE_STYLE, "dashed")

        mock_ConfigService.setString.reset_mock()

        presenter.action_line_style_changed("dotted")
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.LINE_STYLE, "dotted")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_line_width_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_line_width_changed(2)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.LINE_WIDTH, "2")

        mock_ConfigService.setString.reset_mock()

        presenter.action_line_width_changed(3.5)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.LINE_WIDTH, "3.5")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_marker_style_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_marker_style_changed('circle')
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.MARKER_STYLE, "circle")

        mock_ConfigService.setString.reset_mock()

        presenter.action_marker_style_changed('octagon')
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.MARKER_STYLE, "octagon")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_marker_size_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_marker_size_changed('8.0')
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.MARKER_SIZE, "8.0")

        mock_ConfigService.setString.reset_mock()

        presenter.action_marker_size_changed('5.0')
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.MARKER_SIZE, "5.0")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_error_width_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_error_width_changed(2)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.ERROR_WIDTH, "2")

        mock_ConfigService.setString.reset_mock()

        presenter.action_error_width_changed(1.5)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.ERROR_WIDTH, "1.5")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_capsize_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_capsize_changed(2)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.CAPSIZE, "2")

        mock_ConfigService.setString.reset_mock()

        presenter.action_capsize_changed(1.5)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.CAPSIZE, "1.5")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_cap_thickness_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_cap_thickness_changed(2)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.CAP_THICKNESS, "2")

        mock_ConfigService.setString.reset_mock()

        presenter.action_cap_thickness_changed(1.5)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.CAP_THICKNESS, "1.5")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_error_every_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_error_every_changed(2)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.ERROR_EVERY, "2")

        mock_ConfigService.setString.reset_mock()

        presenter.action_error_every_changed(5)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.ERROR_EVERY, "5")

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_legend_every_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_legend_location_changed('best')
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.LEGEND_LOCATION, 'best')

        mock_ConfigService.setString.reset_mock()

        presenter.action_legend_location_changed('upper left')
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.LEGEND_LOCATION, 'upper left')

    @patch(CONFIG_SERVICE_CLASSPATH, new_callable=MockConfigService)
    def test_action_legend_size_changed(self, mock_ConfigService):
        presenter = PlotSettings(None)
        # reset any effects from the constructor
        mock_ConfigService.setString.reset_mock()

        presenter.action_legend_size_changed(10)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.LEGEND_FONT_SIZE, '10')

        mock_ConfigService.setString.reset_mock()

        presenter.action_legend_size_changed(8)
        mock_ConfigService.setString.assert_called_once_with(PlotSettings.LEGEND_FONT_SIZE, '8')


if __name__ == "__main__":
    unittest.main()
