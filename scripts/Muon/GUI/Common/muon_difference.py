# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
# pylint: disable=C0111

class MuonDifference(object):
    """
    Simple structure to store information on a detector group or pair difference.

    - The name is set at initialization and after that cannot be changed.
    - Whether the difference is of two pairs or two groups
    - The difference has two groups or two pairs associated with it,
        cannot have a combination of groups and pairs, and we store their names
    """

    def __init__(self, difference_name, group_or_pair, group_pair_name_1, group_pair_name_2):
        self._difference_name = difference_name
        self._group_or_pair = group_or_pair
        self._group_pair_name_1 = group_pair_name_1
        self._group_pair_name_2 = group_pair_name_2

    @property
    def name(self):
        return self._difference_name

    @property
    def group_or_pair(self):
        return self._group_or_pair

    @property
    def group_pair_1(self):
        return self._group_pair_name_1

    @property
    def group_pair_2(self):
        return self._group_pair_name_2

    @group_or_pair.setter
    def group_or_pair(self, group_or_pair):
        self._group_or_pair = group_or_pair

    @group_pair_1.setter
    def group_pair_1(self, new_name):
        self._group_pair_name_1 = new_name

    @group_pair_2.setter
    def group_pair_2(self, new_name):
        self._group_pair_name_2 = new_name
