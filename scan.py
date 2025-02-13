import os
import sqlite3
import hashlib
from exifOperations import delete_metadata, write_tags, write_text
from getTags import getTag
from getText import ocr_with_paddle

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


def get_image_files_from_directory(directory):
    imageExtensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    return [entry.name for entry in os.scandir(directory) if entry.is_file() and os.path.splitext(entry.name)[1].lower() in imageExtensions]


def calculate_sha256(filename):
    sha256Hash = hashlib.sha256()

    with open(filename, "rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256Hash.update(byte_block)
    return sha256Hash.hexdigest()


def scan(directory, delete, write):
    fileList = get_image_files_from_directory(directory)
    for file in fileList:
        filePath = os.path.normpath(os.path.join(directory, file))
        # Check if it already exists in database
        checkIfExistQuery = "SELECT id FROM images WHERE path LIKE ? AND shaValue LIKE ?"
        cursor.execute(checkIfExistQuery, (directory, calculate_sha256(filePath)))
        result = cursor.fetchall()
        if not result:
            # Delete metadata if checked
            if delete:
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
            if write:
                write_tags(filePath, finalTags)
                write_text(filePath, ocr)

            # Write to database
            insertQuery = "INSERT INTO images (shaValue, path, filename, tags, text) VALUES (?, ?, ?, ?, ?)"
            cursor.execute(insertQuery, (calculate_sha256(filePath), directory, file, finalTags, ocr))
            conn.commit()


conn.close()
