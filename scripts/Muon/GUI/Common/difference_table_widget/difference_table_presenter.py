# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
import re
from Muon.GUI.Common.muon_difference import MuonDifference
from Muon.GUI.Common.utilities.run_string_utils import valid_name_regex
from Muon.GUI.Common.grouping_tab_widget.grouping_tab_widget_model import RowValid
from Muon.GUI.Common.grouping_table_widget.grouping_table_widget_presenter import row_colors, row_tooltips

difference_columns = ['difference_name', 'to_analyse', 'group_or_pair', 'group_pair_1', 'group_pair_2']

class DifferenceTablePresenter(object):

    def __init__(self, view, model):
        self._view = view
        self._model = model

        self._view.on_add_difference_button_clicked(self.handle_add_difference_button_clicked)
        self._view.on_remove_difference_button_clicked(self.handle_remove_difference_button_clicked)
        self._view.on_table_data_changed(self.handle_data_change)

    def enable_editing(self):
        self._view.enable_editing()

    def disable_editing(self):
        self._view.disable_editing()

    def handle_data_change(self, row, col):
        """Handle any data changed in the difference table"""
        table = self._view.get_table_contents()
        changed_item_text = self._view.get_table_item_text(row, col)

        if difference_columns[col] == 'group_or_pair':
            if changed_item_text == 'group':
                if len(self._model.group_names) < 2:
                    self._view.warning_popup("Cannot create a difference of groups as there are less than two groups")
                    table[row][col] = str('pair')
                    return
            else:
                if len(self._model.pair_names) < 2:
                    self._view.warning_popup("Cannot create a difference of pairs as there are less than two pairs")
                    table[row][col] = str('group')
                    return
        if difference_columns[col] == 'group_pair_1':
            if changed_item_text == self._view.get_table_item_text(row, difference_columns.index('group_pair_2')):
                table[row][difference_columns.index('group_pair_2')] = self._model.differences[row].group_pair_1
        if difference_columns[col] == 'group_pair_2':
            if changed_item_text == self._view.get_table_item_text(row, difference_columns.index('group_pair_1')):
                table[row][difference_columns.index('group_pair_1')] = self._model.differences[row].group_pair_2

        self.update_model_from_view(table)
        self.update_view_from_model()

    def update_model_from_view(self, table=None):
        # Get table if not provided
        if not table:
            table = self._view.get_table_contents()
        self._model.clear_differences()
        for entry in table:
            difference = MuonDifference(difference_name=entry[0],
                                        group_or_pair=entry[2],
                                        group_pair_name_1=entry[3],
                                        group_pair_name_2=entry[4])
            self._model.add_difference(difference)

    def update_view_from_model(self):
        self._view.disable_updates()
        self._view.clear()

        for difference in self._model.differences:
            self.add_difference_to_view(difference=difference)

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

    def handle_add_difference_button_clicked(self):
        if (len(self._model.pair_names) == 0 or len(self._model.pair_names) == 1) and (len(self._model.group_names) == 0 or len(self._model.group_names) == 1):
            self._view.warning_popup("At least two groups or two pairs are required to create a difference")
        else:
            new_difference_name = self._view.enter_difference_name()
            if new_difference_name is None: # User did not supply name
                return
            elif new_difference_name in self._model.group_and_pair_names:
                self._view.warning_popup("Groups and pairs must have unique names")
            elif self.validate_difference_name(new_difference_name):
                if len(self._model.group_names) >= 2:
                    # Difference of groups
                    group_or_pair = 'group'
                    group_pair_1 = self._model.group_names[0]
                    group_pair_2 = self._model.group_names[1]
                else:
                    # Difference of pairs
                    group_or_pair = 'pair'
                    group_pair_1 = self._model.pair_names[0]
                    group_pair_2 = self._model.pair_names[1]
                difference = MuonDifference(difference_name=str(new_difference_name),
                                            group_or_pair=group_or_pair,
                                            group_pair_name_1=group_pair_1,
                                            group_pair_name_2=group_pair_2)
                self.add_difference(difference)
                # notify data changed?

    def add_difference(self, difference):
        if self._view.num_rows() > 19:
            self._view.warning_popup("Cannot add more than 20 differences.")
            return
        self.add_difference_to_model(difference)
        self.update_view_from_model()

    def add_difference_to_model(self, difference):
        self._model.add_difference(difference)

    # One more arg is difference, which is instance difference
    def add_difference_to_view(self, difference,to_analyse=False,color=row_colors[RowValid.valid_for_all_runs],
                               tool_tip=row_tooltips[RowValid.valid_for_all_runs]):
        self._view.disable_updates()
        self.update_group_selections()
        self.update_pair_selections()
        # assert is instance
        entry = [str(difference.name), to_analyse, str(difference.group_or_pair),
                 str(difference.group_pair_1), str(difference.group_pair_2)]
        self._view.add_entry_to_table(entry, color, tool_tip)
        self._view.enable_updates()

    def handle_remove_difference_button_clicked(self):
        difference_names = self._view.get_selected_difference_names()
        if not difference_names:
            self.remove_last_row_in_view_and_model()
        else:
            self._view.remove_selected_differences()
            self.remove_selected_rows_in_view_and_model(difference_names)
        # Notify data changed

    def remove_last_row_in_view_and_model(self):
        if self._view.num_rows() > 0:
            self._view.remove_last_row()
            # Remove from analysis etc

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