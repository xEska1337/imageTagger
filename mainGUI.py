import sys
import os
import time
import sqlite3
import qdarktheme
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout, QFrame,
    QProgressBar, QTabWidget, QComboBox, QLineEdit, QListWidget,
    QCheckBox, QMessageBox, QMenu
)
from PyQt6.QtGui import QPixmap, QDesktopServices, QGuiApplication, QColor, QPalette, QCursor
from PyQt6.QtCore import Qt, QUrl, QTimer
from scan import start_scanner
from multiComboBoxWithSearch import MultiSelectComboBoxWithSearch

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

cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shaValue CHAR(64),
                path VARCHAR(2000),
                filename VARCHAR(2000),
                tags VARCHAR(2000),
                text VARCHAR(3000),
                desc VARCHAR(4000)
            )
        ''')
conn.commit()

cursor.execute("INSERT INTO settings (id,deleteMetadata,writeMetadata,autoScan) VALUES (1,0,0,0) ON CONFLICT (id) DO NOTHING")
conn.commit()

searchText = ""
searchTags = []
filterTags = []


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
        QTimer.singleShot(100, self.load_images)
        QTimer.singleShot(100, self.pull_tags)

    def init_images_tab(self):

        layout = QVBoxLayout(self.imageTab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search box
        searchBoxLayout = QHBoxLayout()
        searchBoxLayout.setContentsMargins(5, 5, 5, 5)

        self.searchBox = QLineEdit(self)
        self.searchBox.setPlaceholderText("Search images... (tags:train car cloud text:)")
        self.searchBox.textChanged.connect(self.search_images)
        searchBoxLayout.addWidget(self.searchBox)

        self.combo = MultiSelectComboBoxWithSearch()
        self.combo.setFixedSize(200, 40)
        self.combo.selected_items_changed.connect(self.filter_tags)
        searchBoxLayout.addWidget(self.combo)

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
        self.sortList.currentTextChanged.connect(self.sort_images)
        infoStripLayoutHorizontal.addWidget(self.sortList)

            # Timer when loading
        self.etaTimer = QLabel("", self)
        self.etaTimer.setAlignment(Qt.AlignmentFlag.AlignRight)
        infoStripLayoutHorizontal.addWidget(self.etaTimer)

        infoStripLayout.addLayout(infoStripLayoutHorizontal)
        layout.addLayout(infoStripLayout)

        self.imageWidgets = []
        self.currentColumns = 0
        self.resizeTimer = QTimer(self)
        self.resizeTimer.setSingleShot(True)
        self.resizeTimer.timeout.connect(self.rearrange_grid)

    def load_images(self):
        cursor.execute("SELECT id, path, filename FROM images")
        result = cursor.fetchall()
        if result:
            startTime = time.time()
            self.imageWidgets.clear()
            self.progressBar.setMaximum(len(result))
            self.progressBar.setValue(0)
            self.progressBar.setVisible(True)
            for index, (id, path, filename) in enumerate(result):
                fullPath = os.path.normpath(os.path.join(path, filename))

                pixmap = QPixmap(fullPath)
                if pixmap.isNull():
                    continue

                frame = QFrame(self)
                frame.setObjectName(f"{id}")
                frame.setProperty("visibility", True)
                frame.setProperty("fullPath", fullPath)
                frameLayout = QVBoxLayout(frame)
                frameLayout.setContentsMargins(0, 0, 0, 0)
                frameLayout.setSpacing(0)
                frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #444;
                    }
                    QLabel {
                        padding: 5px;
                        border: none;
                    }
                """)

                imageContent = QLabel(self)
                thumbnail = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                imageContent.setPixmap(thumbnail)
                imageContent.setAlignment(Qt.AlignmentFlag.AlignCenter)

                frame.mousePressEvent = lambda event, path=fullPath: self.open_image(event, path)
                frame.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                frame.customContextMenuRequested.connect(lambda _, path=fullPath: self.show_context_menu(path))

                statsLayout = QHBoxLayout()

                resolutionLabel = QLabel(f"{pixmap.width()} x {pixmap.height()}", self)
                resolutionLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
                statsLayout.addWidget(resolutionLabel)

                size = os.path.getsize(fullPath)
                units = ["B", "KB", "MB", "GB"]
                unitIndex = 0

                while size >= 1024 and unitIndex < len(units) - 1:
                    size /= 1024
                    unitIndex += 1

                sizeLabel = QLabel(f"{size:.2f} {units[unitIndex]}", self)
                sizeLabel.setAlignment(Qt.AlignmentFlag.AlignRight)
                statsLayout.addWidget(sizeLabel)

                filenameLabel = QLabel(filename)
                filenameLabel.setObjectName("filename")
                if len(filename) >= 41:
                    filenameLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
                else:
                    filenameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
                filenameLabel.setStyleSheet("""
                QLabel {
                    max-width: 250px;
                    text-overflow: ellipsis;
                }
                """)
                filenameLabel.setToolTip(filename)

                frameLayout.addWidget(imageContent)
                frameLayout.addLayout(statsLayout)
                frameLayout.addWidget(filenameLabel)
                frame.setLayout(frameLayout)

                self.imageWidgets.append(frame)
                self.gridLayout.addWidget(frame)
                self.progressBar.setValue(index + 1)
                elapsedTime = time.time() - startTime
                remainingTime = (elapsedTime / (index + 1)) * (len(result) - (index + 1))
                self.etaTimer.setText(f"Estimated time remaining: {remainingTime:.1f} sec")

            self.progressBar.setVisible(False)
            self.imageCounter.setText(f"Images: {len(result)}")
            self.rearrange_grid()
            self.sort_images()
            self.etaTimer.setText("")
        else:
            noImageLabel = QLabel("No images to display, scan folder first", self)
            self.gridLayout.addWidget(noImageLabel)

    def rearrange_grid(self):
        if not self.imageWidgets:
            return

        windowWidth = self.width()
        imageSize = 250
        spacing = 10
        columns = max(1, windowWidth // (imageSize + spacing))

        self.currentColumns = columns

        row, col = 0, 0
        for frame in self.imageWidgets:
            if frame.property("visibility"):
                self.gridLayout.addWidget(frame, row, col)
                col += 1
            if col >= columns:
                col = 0
                row += 1

    def resizeEvent(self, a0):
        self.resizeTimer.start(50)
        super().resizeEvent(a0)

    def open_image(self, event, path):
        if event.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def show_context_menu(self, path):
        menu = QMenu(self)
        menu.setStyleSheet("border-radius: 10px;")
        copy = menu.addAction("Copy to clipboard")
        copyPath = menu.addAction("Copy path")
        openPath = menu.addAction("Open file location")
        action = menu.exec(QCursor.pos())
        if action == copy:
            clipboard = QGuiApplication.clipboard()
            pixmap = QPixmap(path)
            clipboard.setPixmap(pixmap)
        elif action == copyPath:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(path)
        elif action == openPath:
            if sys.platform == "win32":
                subprocess.run(["explorer", "/select,", path])
            else:
                subprocess.run(["nautilus", "--select", path])

    def search_images(self):
        if not self.imageWidgets:
            return

        query = self.searchBox.text().lower().strip()

        tagsSearch = ""
        textSearch = query

        if "tags:" in query:
            parts = query.split("tags:")
            if len(parts) > 1:
                tagsPart = parts[1].split("text:")[0].strip()
                tagsSearch = [tag.strip() for tag in tagsPart.split(" ")]

        if "text:" in query:
            parts = query.split("text:")
            if len(parts) > 1:
                textSearch = parts[1].strip()

        global searchText
        searchText = textSearch
        global searchTags
        searchTags = tagsSearch
        self.image_hider()

    def sort_images(self):
        match self.sortList.currentIndex():
            case 0:
                self.imageWidgets.sort(key=lambda f: f.findChild(QLabel, "filename").text().lower())
                self.rearrange_grid()
            case 1:
                self.imageWidgets.sort(key=lambda f: f.findChild(QLabel, "filename").text().lower(), reverse=True)
                self.rearrange_grid()
            case 2:
                self.imageWidgets.sort(key=lambda f: os.path.getsize(f.property("fullPath")))
                self.rearrange_grid()
            case 3:
                self.imageWidgets.sort(key=lambda f: os.path.getsize(f.property("fullPath")), reverse=True)
                self.rearrange_grid()
            case 4:
                self.imageWidgets.sort(key=lambda f: os.path.getctime(f.property("fullPath")), reverse=True)
                self.rearrange_grid()
            case 5:
                self.imageWidgets.sort(key=lambda f: os.path.getctime(f.property("fullPath")))
                self.rearrange_grid()

    def pull_tags(self):
        cursor.execute("SELECT tags FROM images")
        result = cursor.fetchall()
        if result:
            tempTags = []
            for row in result:
                values = row[0].split(';')
                values = [value for value in values if value]
                tempTags.extend(values)

            tags = list(set(tempTags))
            tags.sort()

            self.combo.addItems(tags)

    def filter_tags(self, value):
        global filterTags
        filterTags = value
        self.image_hider()

    def image_hider(self):
        sqlQuery = "SELECT id FROM images WHERE 1=1"

        global searchTags
        global searchText
        if searchTags:
            for tag in searchTags:
                sqlQuery += f" AND tags LIKE '%{tag}%'"

            if searchText != self.searchBox.text().lower().strip():
                sqlQuery += f" AND text LIKE '%{searchText}%'"
        else:
            sqlQuery += f" AND text LIKE '%{searchText}%'"

        global filterTags
        for tag in filterTags:
            sqlQuery += f" AND tags LIKE '%{tag}%'"

        cursor.execute(sqlQuery)
        result = cursor.fetchall()
        if result:
            ids = {str(row[0]) for row in result}
            for frame in self.imageWidgets:
                if not frame.objectName() in ids:
                    frame.setVisible(False)
                    frame.setProperty("visibility", False)
                else:
                    frame.setVisible(True)
                    frame.setProperty("visibility", True)
        else:
            for frame in self.imageWidgets:
                frame.setVisible(False)
                frame.setProperty("visibility", False)

        self.rearrange_grid()

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
        scanButton.clicked.connect(self.scanner)
        databaseButtonLayout.addWidget(scanButton)

        rebuildButton = QPushButton("Rebuild database", self)
        rebuildButton.clicked.connect(self.rebuild_database)
        databaseButtonLayout.addWidget(rebuildButton)

        deleteButton = QPushButton("Delete database", self)
        deleteButton.setStyleSheet("color: red;")
        deleteButton.clicked.connect(self.delete_database)
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

    def scanner(self):
        cursor.execute("SELECT directory FROM settings WHERE id != 1")
        result = cursor.fetchall()
        if result:
            for row in result:
                start_scanner(row[0], self.deleteMetadataCheckbox.isChecked(), self.writeMetadataCheckbox.isChecked())

    def delete_database(self):
        reply = QMessageBox.question(self, 'Confirm Deletion',
                                     f"Are you sure you want to delete image database",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            cursor.execute("DROP TABLE images")
            conn.commit()

    def rebuild_database(self):
        reply = QMessageBox.question(self, 'Confirm Rebuild',
                                     f"Are you sure you want to rebuild image database",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            cursor.execute("DROP TABLE images")
            conn.commit()
            self.scanner()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageTagger()
    window.show()
    sys.exit(app.exec())


conn.close()
