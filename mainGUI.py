import sys
import os
import time
import qdarktheme
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout, QFrame,
    QProgressBar, QTabWidget, QComboBox, QLineEdit, QListWidget,
    QCheckBox
)
from PyQt6.QtGui import QPixmap, QDesktopServices, QClipboard, QGuiApplication, QColor, QPalette
from PyQt6.QtCore import Qt, QUrl, QTimer


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
        #addButton.clicked.connect(self.add_directory)
        buttonLayout.addWidget(addButton)
        removeButton = QPushButton("Remove Directory", self)
        #removeButton.clicked.connect(self.remove_directory)
        buttonLayout.addWidget(removeButton)
        layout.addLayout(buttonLayout)

        # Init directory list
        self.directories = []  # This will hold all selected directories
        #self.load_directories()

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
        self.deleteMetadataCheckbox.setChecked(False)
        #self.deleteMetadataCheckbox.stateChanged.connect(self.checkbox_changed)
        checkboxesLayout.addWidget(self.deleteMetadataCheckbox)

        self.writeMetadataCheckbox = QCheckBox("Write tags to image metadata", self)
        self.writeMetadataCheckbox.setChecked(False)
        #self.writeMetadataCheckbox.stateChanged.connect(self.checkbox_changed)
        checkboxesLayout.addWidget(self.writeMetadataCheckbox)

        self.autoscanCheckbox = QCheckBox("Auto scan new images", self)
        self.autoscanCheckbox.setChecked(False)
        #self.autoscanCheckbox.stateChanged.connect(self.checkbox_changed)
        checkboxesLayout.addWidget(self.autoscanCheckbox)

        secondLayout = QHBoxLayout()
        secondLayout.addLayout(databaseButtonLayout)
        secondLayout.addLayout(checkboxesLayout)

        layout.addLayout(secondLayout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageTagger()
    window.show()
    sys.exit(app.exec())