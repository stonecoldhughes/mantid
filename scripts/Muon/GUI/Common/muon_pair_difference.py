# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
# pylint: disable=C0111
from Muon.GUI.Common.muon_base_difference import MuonBaseDifference
from Muon.GUI.Common.muon_pair import MuonPair

class MuonPairDifference(MuonBaseDifference):
    """
    Blah blah blah
    """

    def __init__(self, difference_name, pair_1, pair_2):

        super().__init__(difference_name)
        self._pair_1 = pair_1
        self._pair_2 = pair_2

    @property
    def pair_1(self):
        return self._pair_1

    @pair_1.setter
    def pair_1(self, pair):
        self._pair_1 = pair

    @property
    def pair_2(self):
        return self._pair_2

    @pair_2.setter
    def pair_2(self, pair):
        self._pair_2 = pair

    # update workspaces need to update workspaces ans recalc?