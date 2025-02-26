from PyQt6.QtWidgets import QComboBox, QLineEdit
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtCore import Qt, QEvent, pyqtSignal


class MultiSelectComboBoxWithSearch(QComboBox):
    selected_items_changed = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.closeOnLineEditClick = False
        self.lineEdit().installEventFilter(self)
        self.view().viewport().installEventFilter(self)

        self.placeholderText = "Select tags"

        self.model().dataChanged.connect(self.update_text)

        self.search_line_edit = QLineEdit(self)
        self.search_line_edit.setPlaceholderText("Search...")
        self.search_line_edit.textChanged.connect(self.filter_items)
        self.search_line_edit.setVisible(False)
        self.setModel(QStandardItemModel(self))
        dummy_item = QStandardItem()
        dummy_item.setText(self.placeholderText)
        dummy_item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.model().appendRow(dummy_item)

    def showPopup(self):
        self.search_line_edit.setVisible(True)
        self.setRootModelIndex(self.model().index(-1, -1))
        self.view().setIndexWidget(self.model().index(0, 0), self.search_line_edit)
        super().showPopup()
        self.closeOnLineEditClick = True

    def hidePopup(self):
        self.search_line_edit.setVisible(False)
        super().hidePopup()
        self.startTimer(100)

    def eventFilter(self, obj, event):
        if obj == self.lineEdit() and event.type() == QEvent.Type.MouseButtonRelease:
            if self.closeOnLineEditClick:
                self.hidePopup()
            else:
                self.showPopup()
            return True
        if obj == self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.position().toPoint())
            item = self.model().itemFromIndex(index)
            if item and index.row() != 0:
                item.setCheckState(
                    Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)
                self.update_text()
                self.selected_items_changed.emit(self.get_selected_items())
                return True
        return False

    def addItem(self, text):
        item = QStandardItem()
        item.setText(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def update_text(self):
        selected_items = [self.model().item(i).text() for i in range(1, self.model().rowCount())
                          if self.model().item(i).checkState() == Qt.CheckState.Checked]
        self.lineEdit().setText(", ".join(selected_items) if selected_items else self.placeholderText)

    def filter_items(self, text):
        for row in range(1, self.model().rowCount()):
            item = self.model().item(row)
            should_hide = text.lower() not in item.text().lower()
            self.view().setRowHidden(row, should_hide)

    def get_selected_items(self):
        return [self.model().item(i).text() for i in range(1, self.model().rowCount())
                if self.model().item(i).checkState() == Qt.CheckState.Checked]
