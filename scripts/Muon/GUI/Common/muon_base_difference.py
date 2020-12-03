# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
# pylint: disable=C0111

class MuonBaseDifference(object):
    """
    Blah blah blah
    """

    def __init__(self, name):

        self._difference_name = name

    @property
    def name(self):
        return self._difference_name