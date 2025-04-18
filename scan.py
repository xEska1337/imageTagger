import os
import sqlite3
import hashlib
import time
import qdarktheme
import ctypes
from exifOperations import delete_metadata, write_tags, write_text
from getTags import getTag
from getText import ocr_with_paddle
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QProgressBar, QLabel, QDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from pathlib import Path

myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

scanWindow = None
isRunning = True


def get_image_files_from_directory(directory):
    imageExtensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    if os.path.isdir(directory):
        return [file.name for file in Path(directory).iterdir() if file.is_file() and file.suffix.lower() in imageExtensions]

    else:
        path = Path(directory)
        if path.is_file() and path.suffix.lower() in imageExtensions:
            return [path.name]
        else:
            os._exit(1)


def calculate_sha256(filename):
    sha256Hash = hashlib.sha256()

    with open(filename, "rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256Hash.update(byte_block)
    return sha256Hash.hexdigest()


class Scanner(QThread):
    itemCount = pyqtSignal(int)
    progressStatus = pyqtSignal()
    processedFile = pyqtSignal(str)
    taskFinished = pyqtSignal()
    avgProcessingTime = pyqtSignal(float)
    processedItemsCount = pyqtSignal(int)

    def __init__(self, directory, delete, write):
        super().__init__()
        self.directory = directory
        self.delete = delete
        self.write = write

    def run(self):
        conn = sqlite3.connect("imageTagger.db")
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shaValue CHAR(64),
                path VARCHAR(2000),
                filename VARCHAR(2000),
                tags VARCHAR(2000),
                text VARCHAR(3000),
                desc VARCHAR(4000),
                favorites BOOLEAN
            )
        ''')
        conn.commit()

        fileList = get_image_files_from_directory(self.directory)
        if not os.path.isdir(self.directory):
            self.directory = os.path.dirname(self.directory)
        startTime = time.time()
        self.itemCount.emit(len(fileList))
        skipped = 0
        for index, file in enumerate(fileList):
            global isRunning
            if not isRunning:
                break
            filePath = os.path.normpath(os.path.join(self.directory, file))
            # Check if it already exists in database
            checkIfExistQuery = "SELECT id FROM images WHERE path LIKE ? AND shaValue LIKE ?"
            cursor.execute(checkIfExistQuery, (self.directory, calculate_sha256(filePath)))
            result = cursor.fetchall()
            if not result:
                self.processedFile.emit(filePath)
                # Delete metadata if checked
                if self.delete:
                    delete_metadata(filePath)

                # Get tags
                tags = getTag(filePath, 0.5)
                finalTags = ""
                for label, prob in tags.items():
                    finalTags += label + ";"
                print(finalTags)

                # Get text
                ocr = ocr_with_paddle(filePath)
                print(ocr)

                # Write to metadata
                if self.write:
                    write_tags(filePath, finalTags)
                    write_text(filePath, ocr)

                # Write to database
                insertQuery = "INSERT INTO images (shaValue, path, filename, tags, text) VALUES (?, ?, ?, ?, ?)"
                cursor.execute(insertQuery, (calculate_sha256(filePath), self.directory, file, finalTags, ocr))
                conn.commit()
            else:
                skipped += 1

            self.progressStatus.emit()
            self.processedItemsCount.emit(index)
            elapsedTime = time.time() - startTime
            self.avgProcessingTime.emit(elapsedTime/(index + 2 - skipped))
        self.taskFinished.emit()
        conn.close()


class ProgressBarWindow(QDialog):
    def __init__(self, directory, delete, write):
        super().__init__()
        qdarktheme.setup_theme()
        self.setWindowTitle("Scanning progress")
        self.setWindowIcon(QIcon("icons/scanIcon.ico"))
        self.setGeometry(100, 100, 300, 100)

        layout = QVBoxLayout()

        self.label = QLabel("", self)
        layout.addWidget(self.label)

        self.progressBar = QProgressBar()
        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progressBar)

        self.avgProcessingTime = QLabel("", self)
        layout.addWidget(self.avgProcessingTime)

        self.itemsLeftLabel = QLabel("", self)
        layout.addWidget(self.itemsLeftLabel)

        self.setLayout(layout)

        self.scan = Scanner(directory, delete, write)
        self.scan.itemCount.connect(self.item_count)
        self.scan.progressStatus.connect(self.update_progress)
        self.scan.avgProcessingTime.connect(self.avg_time)
        self.scan.processedItemsCount.connect(self.items_left)
        self.scan.processedFile.connect(self.label.setText)
        self.scan.taskFinished.connect(self.close)
        self.scan.start()

        self.itemsLeftVar = 0

    def update_progress(self):
        self.progressBar.setValue(self.progressBar.value() + 1)

    def avg_time(self, value):
        self.avgProcessingTime.setText(f"Avg time per item: {value:.1f} sec")

    def item_count(self, value):
        self.progressBar.setMaximum(value)
        self.itemsLeftVar = value

    def items_left(self, value):
        self.itemsLeftLabel.setText(f"Items left: {self.itemsLeftVar - value}")

    def closeEvent(self, a0):
        global isRunning
        isRunning = False
        self.scan.quit()
        self.scan.wait()
        a0.accept()


def start_scanner(directory, delete, write):
    global isRunning
    isRunning = True
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    global scanWindow
    scanWindow = ProgressBarWindow(directory, delete, write)
    scanWindow.show()
    app.exec()

