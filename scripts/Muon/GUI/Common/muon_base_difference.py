# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
# pylint: disable=C0111
from Muon.GUI.Common.ADSHandler.muon_workspace_wrapper import MuonWorkspaceWrapper

class MuonBaseDifference(object):
    """
    Blah blah blah
    """

    def __init__(self, name):

        self._difference_name = name
        self._workspace = {}

    @property
    def name(self):
        return self._difference_name

    @property
    def workspace(self):
        return self._workspace

    @workspace.setter
    def workspace(self, new_workspace):
        if isinstance(new_workspace, MuonWorkspaceWrapper):
            self._workspace = new_workspace
        else:
            raise AttributeError("Attempting to set workspace to type " + str(type(new_workspace))
                                 + " but should be MuonWorkspaceWrapper")