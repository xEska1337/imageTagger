import os
import sqlite3
import hashlib
from exifOperations import delete_metadata, write_tags, write_text
from getTags import getTag
from getText import ocr_with_paddle
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QLabel
from PyQt6.QtCore import Qt, QThread, pyqtSignal

scanWindow = None


def get_image_files_from_directory(directory):
    imageExtensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    return [entry.name for entry in os.scandir(directory) if entry.is_file() and os.path.splitext(entry.name)[1].lower() in imageExtensions]


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
                desc VARCHAR(4000)
            )
        ''')
        conn.commit()

        fileList = get_image_files_from_directory(self.directory)
        self.itemCount.emit(len(fileList))
        for file in fileList:
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

            self.progressStatus.emit()
        self.taskFinished.emit()
        conn.close()


class ProgressBarWindow(QWidget):
    def __init__(self, directory, delete, write):
        super().__init__()
        self.setWindowTitle("Scanning progress")
        self.setGeometry(100, 100, 300, 100)

        layout = QVBoxLayout()

        self.label = QLabel("", self)
        layout.addWidget(self.label)

        self.progressBar = QProgressBar()
        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.progressBar)
        self.setLayout(layout)

        self.scan = Scanner(directory, delete, write)
        self.scan.itemCount.connect(self.progressBar.setMaximum)
        self.scan.progressStatus.connect(self.update_progress)
        self.scan.processedFile.connect(self.label.setText)
        self.scan.taskFinished.connect(self.close)
        self.scan.start()

    def update_progress(self):
        self.progressBar.setValue(self.progressBar.value() + 1)

    def closeEvent(self, a0):
        self.scan.terminate()
        self.scan.wait()
        a0.accept()

def start_scanner(directory, delete, write):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    global scanWindow
    scanWindow = ProgressBarWindow(directory, delete, write)
    scanWindow.show()
    app.exec()

