# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
# pylint: disable=C0111
from Muon.GUI.Common.muon_base_difference import MuonBaseDifference
from Muon.GUI.Common.muon_group import MuonGroup

class MuonGroupDifference(MuonBaseDifference):
    """
    Blah blah blah
    """

    def __init__(self, difference_name, group_1, group_2):

        super().__init__(difference_name)
        self._group_1 = group_1
        self._group_2 = group_2

    @property
    def group_1(self):
        return self._group_1

    @group_1.setter
    def group_1(self, group):
        self._group_1 = group

    @property
    def group_2(self):
        return self._group_2

    @group_2.setter
    def pair_2(self, group):
        self._group_2 = group

    # update workspaces just call update workspace for group 1 and 2