import os
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from scan import start_scanner

imageExtensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
observers = []
pending_scans = {}
scan_lock = threading.Lock()


def scan(file_path, delete, write):
    start_scanner(file_path, delete, write)


class MyHandler(FileSystemEventHandler):
    def __init__(self, delete, write):
        super().__init__()
        self.delete = delete
        self.write = write

    def on_any_event(self, event):
        if event.is_directory:
            return

        file_extension = os.path.splitext(event.src_path)[1].lower()
        if file_extension not in imageExtensions:
            return

        with scan_lock:
            if event.src_path in pending_scans:
                pending_scans[event.src_path].cancel()
            timer = threading.Timer(0.5, self.run_scan, [event.src_path])
            pending_scans[event.src_path] = timer
            timer.start()

    def run_scan(self, file_path):
        try:
            with scan_lock:
                pending_scans.pop(file_path, None)
            scan(file_path, self.delete, self.write)
            print(f"Detected change: {file_path}")
        except Exception as e:
            print(f"Error {file_path}: {e}")


def start_watching(directories, delete, write):
    global observers

    for folder in directories:
        event_handler = MyHandler(delete, write)
        observer = Observer()
        observer.schedule(event_handler, folder, recursive=False)
        observers.append(observer)
        observer.start()
        print(f"Watching: {folder}")


def stop_watching():
    global observers
    print("Stopping observers...")

    with scan_lock:
        for timer in pending_scans.values():
            timer.cancel()
        pending_scans.clear()

    for observer in observers:
        observer.stop()
    for observer in observers:
        observer.join()
    observers = []
