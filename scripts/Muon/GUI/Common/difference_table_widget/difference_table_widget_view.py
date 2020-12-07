# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Signal

from Muon.GUI.Common import message_box
from Muon.GUI.Common.utilities import table_utils

difference_columns = {0: 'difference_name', 1: 'to_analyse', 2: 'group_or_pair', 3: 'group_pair_1', 4: 'group_pair_2'}
inverted_difference_columns = {'difference_name': 0, 'to_analyse': 1, 'group_or_pair': 2, 'group_pair_1': 3, 'group_pair_2': 4}

class DifferenceTableView(QtWidgets.QWidget):

    def warning_popup(self, message):
        message_box.warning(str(message), parent=self)

    def __init__(self, parent=None):
        super(DifferenceTableView, self).__init__(parent)

        self.difference_table = QtWidgets.QTableWidget(self)
        self.set_up_table()
        self.set_up_layout()
        self.difference_table.cellChanged.connect(self.on_cell_changed)

        self._validate_difference_name_entry = lambda text: True
        self._on_table_data_changed = lambda: 0

        # Active groups/pairs that can be selected from the comboboxes
        self._group_selections = []
        self._pair_selections = []

        # Whether the difference table is updating, should not respond to signals if true
        self._updating = False

        # Right click context menu
        self.menu = None
        self._disabled = False
        self.add_difference_action = None
        self.remove_difference_action = None

    def set_up_table(self):
        self.difference_table.setColumnCount(5)
        self.difference_table.setHorizontalHeaderLabels(["Difference Name", "Analyse (plot/fit)", "Group or Pair",
                                                         "Group/Pair 1", "Group/Pair 2"])
        header = self.difference_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        vertical_headers = self.difference_table.verticalHeader()
        vertical_headers.setSectionsMovable(False)
        vertical_headers.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_headers.setVisible(True)

        self.difference_table.horizontalHeaderItem(0).setToolTip("The name of the difference :"
                                                              "\n    - The name must be unique across all groups/pairs/differences"
                                                              "\n    - The name can only use digits, characters and _")
        self.difference_table.horizontalHeaderItem(1).setToolTip("Whether to include this difference in the analysis")
        self.difference_table.horizontalHeaderItem(2).setToolTip("Whether the difference is between groups or pairs")
        self.difference_table.horizontalHeaderItem(3).setToolTip("Group/Pair 1 of the difference, selected from the grouping/pairing table")
        self.difference_table.horizontalHeaderItem(4).setToolTip("Group/Pair 2 of the difference, selected from the grouping/pairing table")

    def set_up_layout(self):
        self.setObjectName("DifferenceTableView")
        self.resize(500,500)

        self.add_difference_button = QtWidgets.QToolButton()
        self.remove_difference_button = QtWidgets.QToolButton()

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.add_difference_button.sizePolicy().hasHeightForWidth())
        size_policy.setHeightForWidth(self.remove_difference_button.sizePolicy().hasHeightForWidth())

        self.add_difference_button.setSizePolicy(size_policy)
        self.add_difference_button.setObjectName("addDifferenceButton")
        self.add_difference_button.setToolTip("Add a difference to the end of the table")
        self.add_difference_button.setText("+")

        self.remove_difference_button.setSizePolicy(size_policy)
        self.remove_difference_button.setObjectName("removeDifferenceButton")
        self.remove_difference_button.setToolTip("Remove selected/last difference(s) from the table")
        self.remove_difference_button.setText("-")

        self.horizontal_layout = QtWidgets.QHBoxLayout()
        self.horizontal_layout.setObjectName("horizontalLayout")
        self.horizontal_layout.addWidget(self.add_difference_button)
        self.horizontal_layout.addWidget(self.remove_difference_button)
        self.spacer_item = QtWidgets.QSpacerItem(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.horizontal_layout.addItem(self.spacer_item)
        self.horizontal_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.vertical_layout = QtWidgets.QVBoxLayout(self)
        self.vertical_layout.setObjectName("verticalLayout")
        self.vertical_layout.addWidget(self.difference_table)
        self.vertical_layout.addLayout(self.horizontal_layout)

        self.setLayout(self.vertical_layout)

    def num_rows(self):
        return self.difference_table.rowCount()

    def num_cols(self):
        return self.difference_table.columnCount()

    def update_group_selections(self, group_name_list):
        self._group_selections = group_name_list

    def update_pair_selections(self, pair_name_list):
        self._pair_selections = pair_name_list

    def clear(self):
        # Go backwards to preserve indices
        for row in reversed(range(self.num_rows())):
            self.difference_table.removeRow(row)

    def difference_type(self, row):
        self.difference_table.cellWidget(row,inverted_difference_columns['group_or_pair']).currentText()

    def add_entry_to_table(self, row_entries, color=(255,255,255), tooltip=''):
        assert len(row_entries) == self.difference_table.columnCount()
        q_color = QtGui.QColor(*color, alpha=127)
        q_brush = QtGui.QBrush(q_color)
        is_group = False # Flag for setting combo boxes in table for group pair selection

        row_position = self.difference_table.rowCount()
        self.difference_table.insertRow(row_position)
        for i, entry in enumerate(row_entries):
            item = QtWidgets.QTableWidgetItem(entry)
            item.setBackground(q_brush)
            item.setToolTip(tooltip)

            if difference_columns[i] == 'difference_name':
                difference_name_widget = table_utils.ValidatedTableItem(self._validate_difference_name_entry)
                difference_name_widget.setText(entry)
                self.difference_table.setItem(row_position, i, difference_name_widget)
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            if difference_columns[i] == 'to_analyse':
                if entry:
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
            if difference_columns[i] == 'group_or_pair':
                group_or_pair_selector = QtWidgets.QComboBox(self)
                group_or_pair_selector.setToolTip("Select whether the difference is between two groups or two pairs")
                group_or_pair_selector.addItems(['group','pair'])
                # ensure change in selection sends an update signal
                group_or_pair_selector.currentIndexChanged.connect(lambda: self.on_cell_changed(row_position,2))
                group_or_pair_selector.setCurrentIndex(group_or_pair_selector.findText(entry))
                self.difference_table.setCellWidget(row_position, i, group_or_pair_selector)

                # Set flag to determine whether to use groups or pairs for combobox selection
                if entry == 'group':
                    is_group = True
            if difference_columns[i] == 'group_pair_1':
                if is_group:
                    group_pair_1_selector = self._group_selection_cell_widget()
                else:
                    group_pair_1_selector = self._pair_selection_cell_widget()
                # ensure change in selection sends an update signal
                group_pair_1_selector.currentIndexChanged.connect(lambda: self.on_cell_changed(row_position,3))
                group_pair_1_selector.setCurrentIndex(group_pair_1_selector.findText(entry))
                self.difference_table.setCellWidget(row_position, i, group_pair_1_selector)
            if difference_columns[i] == 'group_pair_2':
                if is_group:
                    group_pair_2_selector = self._group_selection_cell_widget()
                else:
                    group_pair_2_selector = self._pair_selection_cell_widget()
                # ensure change in selection sends an update signal
                group_pair_2_selector.currentIndexChanged.connect(lambda: self.on_cell_changed(row_position,4))
                group_pair_2_selector.setCurrentIndex(group_pair_2_selector.findText(entry))
                self.difference_table.setCellWidget(row_position, i, group_pair_2_selector)
            self.difference_table.setItem(row_position, i, item)

    def get_table_contents(self):
        if self._updating:
            return []
        ret = [[None for _ in range(self.num_cols())] for _ in range(self.num_rows())]
        for row in range(self.num_rows()):
            for col in range(self.num_cols()):
                # Handle widgets separately
                if difference_columns[col] == "group_or_pair" or difference_columns[col] == "group_pair_1" or difference_columns[col] == "group_pair_2":
                    ret[row][col] = str(self.difference_table.cellWidget(row, col).currentText())
                else: # non-widget cell
                    ret[row][col] = str(self.difference_table.item(row,col).text())
        return ret

    def get_table_item(self, row, col):
        return self.difference_table.item(row, col)

    def get_table_item_text(self, row, col):
        # If widget handle separately
        if difference_columns[col] == "group_or_pair" or difference_columns[col] == "group_pair_1" or difference_columns[col] == "group_pair_2":
            return str(self.difference_table.cellWidget(row, col).currentText())
        else: # non-widget cell
            return str(self.difference_table.item(row, col).text())

    def set_group_or_pair(self, row, text):
        self.difference_table.cellWidget(row, inverted_difference_columns['group_or_pair']).setCurrentIndex(
            self.difference_table.cellWidget(row, inverted_difference_columns['group_or_pair']).findText(text))

    def set_group_pair_selection_combo_boxes(self, row, type):
        col_1 = inverted_difference_columns['group_pair_1']
        col_2 = inverted_difference_columns['group_pair_2']
        self.difference_table.cellWidget(row, col_1).blockSignals(True)
        self.difference_table.cellWidget(row, col_2).blockSignals(True)
        self.difference_table.cellWidget(row, col_1).clear()
        self.difference_table.cellWidget(row, col_2).clear()
        if type == 'groups':
            self.difference_table.cellWidget(row, col_1).addItems(self._group_selections)
            self.difference_table.cellWidget(row, col_2).addItems(self._group_selections)
        else:
            self.difference_table.cellWidget(row, col_1).addItems(self._pair_selections)
            self.difference_table.cellWidget(row, col_2).addItems(self._pair_selections)
        self.difference_table.cellWidget(row, col_1).blockSignals(False)
        self.difference_table.cellWidget(row, col_2).blockSignals(False)

    def _group_selection_cell_widget(self):
        """Combo box for group selection"""
        selector = QtWidgets.QComboBox(self)
        selector.setToolTip("Select a group from the grouping table")
        selector.addItems(self._group_selections)
        return selector

    def _pair_selection_cell_widget(self):
        """Combo box for pair selection"""
        selector = QtWidgets.QComboBox(self)
        selector.setToolTip("Select a pair from the pairing table")
        selector.addItems(self._pair_selections)
        return selector

    # ------------------------------------------------------------------------------------------------------------------
    # Signal / Slot connections
    # ------------------------------------------------------------------------------------------------------------------

    def on_add_difference_button_clicked(self, slot):
        self.add_difference_button.clicked.connect(slot)

    def on_remove_difference_button_clicked(self, slot):
        self.remove_difference_button.clicked.connect(slot)

    def on_cell_changed(self, _row, _col):
        if not self._updating:
            self._on_table_data_changed(_row, _col)

    def on_table_data_changed(self, slot):
        self._on_table_data_changed = slot

    # ------------------------------------------------------------------------------------------------------------------
    # Context Menu
    # ------------------------------------------------------------------------------------------------------------------

    def contextMenuEvent(self, _event):
        """Overridden method for right click"""
        self.menu = QtWidgets.QMenu(self)

        self.add_difference_action = self._context_menu_add_difference_action(self.add_difference_button.clicked.emit)
        self.remove_difference_action = self._context_menu_remove_difference_action(self.remove_difference_button.clicked.emit)

        if self._disabled:
            self.add_difference_action.setEnabled(False)
            self.remove_difference_action.setEnabled(False)

        self.menu.addAction(self.add_difference_action)
        self.menu.addAction(self.remove_difference_action)
        self.menu.popup(QtGui.QCursor.pos())

    def _context_menu_add_difference_action(self, slot):
        add_difference_action = QtWidgets.QAction('Add Difference', self)
        add_difference_action.setCheckable(False)
        if len(self._get_selected_row_indices()) > 0:
            add_difference_action.setEnabled(False)
        add_difference_action.triggered.connect(slot)
        return add_difference_action

    def _context_menu_remove_difference_action(self, slot):
        if len(self._get_selected_row_indices()) > 1:
            # Use plural
            remove_pair_action = QtWidgets.QAction('Remove Differences', self)
        else:
            remove_pair_action = QtWidgets.QAction('Remove Difference', self)
        if self.num_rows() == 0:
            remove_pair_action.setEnabled(False)
        remove_pair_action.triggered.connect(slot)
        return remove_pair_action

    # ------------------------------------------------------------------------------------------------------------------
    # Adding / Removing differences
    # ------------------------------------------------------------------------------------------------------------------

    def remove_selected_differences(self):
        indices = self._get_selected_row_indices()
        for index in reversed(sorted(indices)):
            self.difference_table.removeRow(index)

    def remove_last_row(self):
        last_row_index = self.difference_table.rowCount() - 1
        if last_row_index >= 0:
            self.difference_table.removeRow(last_row_index)

    def get_selected_difference_names(self):
        indexes = self._get_selected_row_indices()
        return [str(self.difference_table.item(i,0).text()) for i in indexes]

    def enter_difference_name(self):
        new_difference_name, ok = QtWidgets.QInputDialog.getText(self, 'Difference Name', 'Enter name of new difference:')
        if ok:
            return new_difference_name

    def _get_selected_row_indices(self):
        return list(set(index.row() for index in self.difference_table.selectedIndexes()))

    # ------------------------------------------------------------------------------------------------------------------
    # Enabling / Disabling the table
    # ------------------------------------------------------------------------------------------------------------------

    def enable_updates(self):
        """Allow update signals to be sent"""
        self._updating = False

    def disable_updates(self):
        """Prevent udpate signals being sent"""
        self._updating = True

    def enable_editing(self):
        self.disable_updates()
        self._disabled = False
        self._enable_all_buttons()
        self.enable_updates()

    def disable_editing(self):
        self.disable_updates()
        self._disabled = True
        self._disable_all_buttons()
        self.enable_updates()

    def _enable_all_buttons(self):
        self.add_difference_button.setEnabled(True)
        self.remove_difference_button.setEnabled(True)

    def _disable_all_buttons(self):
        self.add_difference_button.setEnabled(False)
        self.remove_difference_button.setEnabled(False)

