# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
import re
from Muon.GUI.Common.muon_group_difference import MuonGroupDifference
from Muon.GUI.Common.muon_pair_difference import MuonPairDifference
from Muon.GUI.Common.muon_group import MuonGroup
from mantidqt.utils.observer_pattern import GenericObservable
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

        self._dataChangedNotifier = lambda: 0

        self.selected_difference_group_changed_notifier = GenericObservable()

    def enable_editing(self):
        self._view.enable_editing()

    def disable_editing(self):
        self._view.disable_editing()

    def on_data_changed(self, notifier):
        self._dataChangedNotifier = notifier

    def notify_data_changed(self):
        self._dataChangedNotifier()

    def handle_data_change(self, row, col):
        """Handle any data changed in the difference table"""
        table = self._view.get_table_contents()
        changed_item_text = self._view.get_table_item_text(row, col)
        update_model = True

        if difference_columns[col] == 'to_analyse':
            update_model = False
            if table[row][2] == 'group':
                self.to_analyse_data_checkbox_changed_group_difference(self._view.get_table_item(row, col).checkState(), self._view.get_table_item_text(row, 0))
            else:
                pass
        if difference_columns[col] == 'group_or_pair':
            if changed_item_text == 'group':
                if len(self._model.group_names) < 2:
                    self._view.set_group_or_pair(row, str('pair'))
                    self._view.warning_popup("Cannot create a difference of groups as there are less than two groups")
                    return
                table[row][2] = str('group')
                table[row][3] = self._model.group_names[0]
                table[row][4] = self._model.group_names[1]
                self.update_group_selections()
                self._view.set_group_pair_selection_combo_boxes(row, 'groups')
            else:
                if len(self._model.pair_names) < 2:
                    self._view.set_group_or_pair(row, str('group')) # update name?
                    self._view.warning_popup("Cannot create a difference of pairs as there are less than two pairs")
                    return
                table[row][2] = str('pair')
                table[row][3] = self._model.pair_names[0]
                table[row][4] = self._model.pair_names[1]
                self.update_pair_selections()
                self._view.set_group_pair_selection_combo_boxes(row, 'pairs')
        if difference_columns[col] == 'group_pair_1':
            if changed_item_text == self._view.get_table_item_text(row, difference_columns.index('group_pair_2')):
                if isinstance(self._model.differences[row], MuonGroupDifference):
                    table[row][difference_columns.index('group_pair_2')] = self._model.differences[row].group_1
                elif isinstance(self._model.differences[row], MuonPairDifference):
                    table[row][difference_columns.index('group_pair_2')] = self._model.differences[row].pair_1
                else:
                    raise ValueError('Cannot swap group or pair')
        if difference_columns[col] == 'group_pair_2':
            if changed_item_text == self._view.get_table_item_text(row, difference_columns.index('group_pair_1')):
                if isinstance(self._model.differences[row], MuonGroupDifference):
                    table[row][difference_columns.index('group_pair_1')] = self._model.differences[row].group_2
                elif isinstance(self._model.differences[row], MuonPairDifference):
                    table[row][difference_columns.index('group_pair_1')] = self._model.differences[row].pair_2
                else:
                    raise ValueError('Cannot swap group or pair')

        if update_model:
            self.update_model_from_view(table)

        self.update_view_from_model()

    def update_model_from_view(self, table=None):
        if not table:
            table = self._view.get_table_contents()
        self._model.clear_differences()
        for entry in table:
            if entry[2] == 'group':
                difference = MuonGroupDifference(difference_name=entry[0],
                                                 group_1=entry[3],
                                                 group_2=entry[4])
                self._model.add_group(difference)
            elif entry[2] == 'pair':
                pass
            else:
                raise ValueError('Cannot add difference')

    def update_view_from_model(self):
        self._view.disable_updates()
        self._view.clear()

        for difference in self._model.differences:
            analyse = True if difference.name in self._model.selected_groups else False
            self.add_difference_to_view(difference=difference, to_analyse=analyse)

        self._view.enable_updates()

    def update_group_selections(self):
        groups = [group.name for group in self._model.groups if isinstance(group, MuonGroup)]
        self._view.update_group_selections(groups)

    def update_pair_selections(self):
        pairs = self._model.pair_names # Need to make sure doesn't include diffs of pairs when implemented
        self._view.update_pair_selections(pairs)

    def to_analyse_data_checkbox_changed_group_difference(self, state, difference_name):
        difference_added = True if state == 2 else False
        if difference_added:
            self._model.add_group_to_analysis(difference_name)
        else:
            self._model.remove_group_from_analysis(difference_name)

        group_info = {'is_added': difference_added, 'name': difference_name}
        self.selected_difference_group_changed_notifier.notify_subscribers(group_info)

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
                is_group = True
                if len(self._model.group_names) >= 2:
                    # Difference of groups
                    # Might need to adjust for the fact that differences can be added in group names
                    group_pair_1 = self._model.group_names[0]
                    group_pair_2 = self._model.group_names[1]
                else:
                    # Difference of pairs
                    # Might need to adjust for the fact that differences can be added in group names
                    group_pair_1 = self._model.pair_names[0]
                    group_pair_2 = self._model.pair_names[1]
                if is_group:
                    difference = MuonGroupDifference(new_difference_name,group_pair_1,group_pair_2)
                else:
                    pass # Pair to be implemented
                self.add_difference(difference)
                # notify data changed?

    def add_difference(self, difference):
        if self._view.num_rows() > 19:
            self._view.warning_popup("Cannot add more than 20 differences.")
            return
        self.add_difference_to_model(difference)
        self.update_view_from_model()
        self.notify_data_changed()

    def add_difference_to_model(self, difference):
        # If group difference add group, otherwise add pair
        if isinstance(difference, MuonGroupDifference):
            self._model.add_group(difference)
        else:
            pass

    def add_difference_to_view(self, difference,to_analyse=False,color=row_colors[RowValid.valid_for_all_runs],
                               tool_tip=row_tooltips[RowValid.valid_for_all_runs]):
        self._view.disable_updates()
        self.update_group_selections()
        self.update_pair_selections()
        if isinstance(difference, MuonGroupDifference):
            entry = [str(difference.name), to_analyse, str('group'),
                     str(difference.group_1), str(difference.group_2)]
        elif isinstance(difference,MuonPairDifference):
            entry = [str(difference.name), to_analyse, str('pair'),
                     str(difference.pair_1), str(difference.pair_2)]
        else:
            raise ValueError('Cannot add difference')

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
        self.notify_data_changed()

    def remove_last_row_in_view_and_model(self):
        if self._view.num_rows() > 0:
            name = self._view.get_table_contents()[-1][0]
            self._view.remove_last_row()
            self._model.remove_differences_by_name([name])
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