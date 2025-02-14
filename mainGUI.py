import sys
import os
import time
import sqlite3
import qdarktheme
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout, QFrame,
    QProgressBar, QTabWidget, QComboBox, QLineEdit, QListWidget,
    QCheckBox, QMessageBox
)
from PyQt6.QtGui import QPixmap, QDesktopServices, QClipboard, QGuiApplication, QColor, QPalette
from PyQt6.QtCore import Qt, QUrl, QTimer

conn = sqlite3.connect("imageTagger.db")
cursor = conn.cursor()

cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            directory VARCHAR(3000),
            deleteMetadata BOOLEAN,
            writeMetadata BOOLEAN,
            autoScan BOOLEAN
        )
    ''')
conn.commit()

cursor.execute("INSERT INTO settings (id,deleteMetadata,writeMetadata,autoScan) VALUES (1,0,0,0) ON CONFLICT (id) DO NOTHING")
conn.commit()


class ImageTagger(QWidget):

    def __init__(self):
        super().__init__()

        # Dark theme
        qdarktheme.setup_theme()
        darkPalette = QPalette()
        darkPalette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        self.setPalette(darkPalette)

        self.setWindowTitle("Image Tagger")
        self.setGeometry(100, 100, 900, 650)

        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)

        # Tabs
        self.tabs = QTabWidget()

        self.tabs.setStyleSheet("""
            QTabWidget::pane {
            border-left: none;
            border-right: none;
            border-bottom: none;
            background: transparent;
            }
        """)

        self.imageTab = QWidget()
        self.settingTab = QWidget()

        self.tabs.addTab(self.imageTab, "Images")
        self.tabs.addTab(self.settingTab, "Settings")

        mainLayout.addWidget(self.tabs)

        # Init tabs
        self.init_images_tab()
        self.init_settings_tab()

    def init_images_tab(self):

        layout = QVBoxLayout(self.imageTab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search box
        searchBoxLayout = QHBoxLayout()
        searchBoxLayout.setContentsMargins(5, 5, 5, 5)

        self.searchBox = QLineEdit(self)
        self.searchBox.setPlaceholderText("Search images...")
        #self.searchBox.textChanged.connect(self.filter_images)
        searchBoxLayout.addWidget(self.searchBox)

        layout.addLayout(searchBoxLayout)

        # Images area
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("border: none;")

        layout.addWidget(self.scrollArea)

        self.container = QWidget()
        self.scrollArea.setWidget(self.container)

        self.gridLayout = QGridLayout(self.container)
        self.container.setLayout(self.gridLayout)

        # Info strip
        infoStripLayout = QVBoxLayout()
        infoStripLayout.setContentsMargins(5, 5, 5, 5)

            # Progress bar
        self.progressBar = QProgressBar(self)
        self.progressBar.setVisible(False)
        infoStripLayout.addWidget(self.progressBar)

        infoStripLayoutHorizontal = QHBoxLayout()

            # Image count
        self.imageCounter = QLabel("Images: 0", self)
        self.imageCounter.setAlignment(Qt.AlignmentFlag.AlignLeft)
        infoStripLayoutHorizontal.addWidget(self.imageCounter)

            # Sorting options
        self.sortList = QComboBox()
        self.sortList.addItems(["Name (A-Z)", "Name (Z-A)", "Size (Smallest First)", "Size (Largest First)", "Date (Newest First)", "Date (Oldest First)"])
        #self.sortList.currentTextChanged.connect(self.sort_images)
        infoStripLayoutHorizontal.addWidget(self.sortList)

            # Timer when loading
        self.etaTimer = QLabel("", self)
        self.etaTimer.setAlignment(Qt.AlignmentFlag.AlignRight)
        infoStripLayoutHorizontal.addWidget(self.etaTimer)

        infoStripLayout.addLayout(infoStripLayoutHorizontal)
        layout.addLayout(infoStripLayout)

    def init_settings_tab(self):

        layout = QVBoxLayout(self.settingTab)

        # Included directories
        self.label = QLabel("Included directories:", self)
        layout.addWidget(self.label)

        self.directoryList = QListWidget(self)
        self.directoryList.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.directoryList)

        buttonLayout = QHBoxLayout()
        addButton = QPushButton("Add Directory", self)
        addButton.setStyleSheet("color: green;")
        addButton.clicked.connect(self.add_directory)
        buttonLayout.addWidget(addButton)
        removeButton = QPushButton("Remove Directory", self)
        removeButton.setStyleSheet("color: red;")
        removeButton.clicked.connect(self.remove_directory)
        buttonLayout.addWidget(removeButton)
        layout.addLayout(buttonLayout)

        # Init directory list
        self.directories = []  # This will hold all selected directories
        self.load_directories()

        # Database action buttons
        databaseButtonLayout = QVBoxLayout()

        label = QLabel("Database actions:", self)
        databaseButtonLayout.addWidget(label)

        scanButton = QPushButton("Scan directories", self)
        #scanButton.clicked.connect(self.scan)
        databaseButtonLayout.addWidget(scanButton)

        rebuildButton = QPushButton("Rebuild database", self)
        #rebuildButton.clicked.connect(self.rebuild)
        databaseButtonLayout.addWidget(rebuildButton)

        deleteButton = QPushButton("Delete database", self)
        deleteButton.setStyleSheet("color: red;")
        #deleteButton.clicked.connect(self.delete_database)
        databaseButtonLayout.addWidget(deleteButton)

        # Settings checkboxes
        checkboxesLayout = QVBoxLayout()

        label2 = QLabel("Settings:", self)
        checkboxesLayout.addWidget(label2)

        self.deleteMetadataCheckbox = QCheckBox("Delete all metadata from scanned images", self)
        self.deleteMetadataCheckbox.stateChanged.connect(self.checkbox_changed)
        checkboxesLayout.addWidget(self.deleteMetadataCheckbox)

        self.writeMetadataCheckbox = QCheckBox("Write tags to image metadata", self)
        self.writeMetadataCheckbox.stateChanged.connect(self.checkbox_changed)
        checkboxesLayout.addWidget(self.writeMetadataCheckbox)

        self.autoscanCheckbox = QCheckBox("Auto scan new images", self)
        self.autoscanCheckbox.stateChanged.connect(self.checkbox_changed)
        checkboxesLayout.addWidget(self.autoscanCheckbox)

        self.load_checkbox_state()

        secondLayout = QHBoxLayout()
        secondLayout.addLayout(databaseButtonLayout)
        secondLayout.addLayout(checkboxesLayout)

        layout.addLayout(secondLayout)

    def add_directory(self):
        newFolderPath = QFileDialog.getExistingDirectory(self, "Select Folder")
        if newFolderPath:
            if newFolderPath not in self.directories:
                self.directories.insert(0, newFolderPath)
                # Update the QListWidget
                self.refresh_list()
                cursor.execute("INSERT INTO settings (directory) VALUES (?)", (newFolderPath,))
                conn.commit()
            else:
                QMessageBox.warning(self, "Directory Already Added", "This directory is already added.")

    def remove_directory(self):
        selectedItems = self.directoryList.selectedItems()
        if not selectedItems:
            QMessageBox.warning(self, "No Selection", "Please select a directory to remove.")
            return

        selectedDirectory = selectedItems[0].text()

        reply = QMessageBox.question(self, 'Confirm Deletion',
                                     f"Are you sure you want to remove '{selectedDirectory}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.directories.remove(selectedDirectory)
            self.refresh_list()
            cursor.execute("DELETE FROM settings WHERE directory=?", (selectedDirectory,))
            conn.commit()

    def refresh_list(self):
        self.directoryList.clear()
        for directory in self.directories:
            self.directoryList.addItem(directory)

    def load_checkbox_state(self):
        cursor.execute("SELECT deleteMetadata, writeMetadata, autoScan FROM settings WHERE id = 1")
        result = cursor.fetchone()
        if result:
            self.deleteMetadataCheckbox.setChecked(bool(result[0]))
            self.writeMetadataCheckbox.setChecked(bool(result[1]))
            self.autoscanCheckbox.setChecked(bool(result[2]))

    def checkbox_changed(self):
        cursor.execute("UPDATE settings SET deleteMetadata = ?, writeMetadata = ?, autoScan = ? WHERE id = 1", (int(self.deleteMetadataCheckbox.isChecked()), int(self.writeMetadataCheckbox.isChecked()), int(self.autoscanCheckbox.isChecked())))
        conn.commit()

    def load_directories(self):
        cursor.execute("SELECT directory FROM settings WHERE id != 1")
        result = cursor.fetchall()
        if result:
            for row in result:
                self.directories.insert(0, row[0])
            self.refresh_list()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageTagger()
    window.show()
    sys.exit(app.exec())


conn.close()
