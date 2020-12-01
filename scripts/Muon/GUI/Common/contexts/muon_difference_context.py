# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +

class MuonDifferenceContext(object):

    def __init__(self):
        self._differences = []
        self._selected_differences = []

    @property
    def differences(self):
        return self._differences

    @property
    def selected_differences(self):
        return self._selected_differences

    @selected_differences.setter
    def selected_differences(self):
        return self._selected_differences

    def clear(self):
        self._differences = []

    def add_difference(self, difference):
        self._differences.append(difference)
