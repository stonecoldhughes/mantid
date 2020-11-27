# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
from qtpy import QtCore
from qtpy.QtWidgets import QApplication
from Muon.GUI.Common.usage_report import report_interface_startup
import sys


def open_interface(Interface, name):
    widgets = QApplication.topLevelWidgets()
    application_names = [app.objectName() for app in widgets]
    if name in application_names:
        interface = widgets[application_names.index(name)]
        interface.setWindowState(interface.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        interface.activateWindow()
        interface.show()
    else:
        if 'workbench' in sys.modules:
            from workbench.config import get_window_config
            parent, flags = get_window_config()
        else:
            parent, flags = None, None
            parent = None
        gui = Interface(parent=parent, window_flags=flags)
        report_interface_startup(name)
        gui.setObjectName(name)
        gui.show()
