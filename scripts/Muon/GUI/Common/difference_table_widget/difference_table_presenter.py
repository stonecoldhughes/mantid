# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
import re
from Muon.GUI.Common.utilities.run_string_utils import valid_name_regex
from Muon.GUI.Common.grouping_tab_widget.grouping_tab_widget_model import RowValid
from Muon.GUI.Common.grouping_table_widget.grouping_table_widget_presenter import row_colors, row_tooltips

class DifferenceTablePresenter(object):

    def __init__(self, view, model):
        self._view = view
        self._model = model

        self._view.on_add_difference_button_clicked(self.handle_add_difference_button_clicked)

    def enable_editing(self):
        self._view.enable_editing()

    def disable_editing(self):
        self._view.disable_editing()

    def update_view_from_model(self):
        self._view.disable_updates()
        self._view.clear()

        #for difference in self._model.differences:

        self.add_difference_to_view()

        self._view.enable_updates()

    def update_group_selections(self):
        groups = self._model.group_names
        self._view.update_group_selections(groups)

    def update_pair_selections(self):
        pairs = self._model.pair_names
        self._view.update_pair_selections(pairs)

    # ------------------------------------------------------------------------------------------------------------------
    # Add / Remove differences
    # ------------------------------------------------------------------------------------------------------------------

    def handle_add_difference_button_clicked(self, difference_1='', difference_2=''):
        if (len(self._model.pair_names) == 0 or len(self._model.pair_names) == 1) and (len(self._model.group_names) == 0 or len(self._model.group_names) == 1):
            self._view.warning_popup("At least two groups or two pairs are required to create a difference")
        else:
            new_difference_name = self._view.enter_difference_name()
            if new_difference_name is None: # User did not supply name
                return
            elif new_difference_name in self._model.group_and_pair_names:
                self._view.warning_popup("Groups and pairs must have unique names")
            elif self.validate_difference_name(new_difference_name):
                if len(self._model.group_names) > 2:
                    # Difference of groups
                    pass
                else:
                    # Difference of pairs
                    pass
                self.add_difference()

    def add_difference(self):
        if self._view.num_rows() > 19:
            self._view.warning_popup("Cannot add more than 20 differences.")
            return
        self.add_difference_to_model()
        self.update_view_from_model()

    def add_difference_to_model(self):
        pass

    # One more arg is difference, which is instance difference
    def add_difference_to_view(self, to_analyse=False,color=row_colors[RowValid.valid_for_all_runs],
                               tool_tip=row_tooltips[RowValid.valid_for_all_runs]):
        self._view.disable_updates()
        self.update_group_selections()
        self.update_pair_selections()
        # assert is instance
        # create dict of entry
        entry = [str('dummy'), True, str('group'), str('foo'), str('bar')]
        # add entry to table
        self._view.add_entry_to_table(entry, color, tool_tip)
        self._view.enable_updates()

    def handle_remove_button_clicked(self):
        difference_names = self._view.get_selected_difference_names()
        if not difference_names:
            self.remove_last_row_in_view_and_model()
        else:
            self.remove_selected_rows_in_view_and_model(difference_names)
        # Notify data changed

    def remove_last_in_view_and_model(self):
        pass

    def remove_selected_rows_in_view_and_model(self, difference_names):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Table entry validation
    # ------------------------------------------------------------------------------------------------------------------

    def validate_difference_name(self, text):
        if not re.match(valid_name_regex, text):
            self._view.warning_popup("Difference names should only contain characters, digits and _")
            return False
        if self._is_edited_name_duplicated(text):
            self._view.warning_popup("Groups and pairs must have unique names")
            return False
        return True

    def _is_edited_name_duplicated(self, new_name):
        is_name_column_being_edited = self._view.difference_table.currentColumn() == 0
        is_name_unique = (sum(
            [new_name == name for name in self._model.group_and_pair_names]) == 0)
        return is_name_column_being_edited and not is_name_unique