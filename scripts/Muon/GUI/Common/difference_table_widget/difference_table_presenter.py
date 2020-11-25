# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +

class DifferenceTablePresenter(object):

    def __init__(self, view, model):
        self._view = view
        self._model = model

        self._view.on_add_difference_button_clicked(self.handle_add_difference_button_clicked)

    def enable_editing(self):
        self._view.enable_editing()

    def disable_editing(self):
        self._view.disable_editing()

    # ------------------------------------------------------------------------------------------------------------------
    # Add / Remove differences
    # ------------------------------------------------------------------------------------------------------------------

    def handle_add_difference_button_clicked(self):
        if (len(self._model.pair_names) == 0 or len(self._model.pair_names) == 1) and (len(self._model.group_names) == 0 or len(self._model.group_names) == 1):
            self._view.warning_popup("At least two groups or two pairs are required to create a difference")