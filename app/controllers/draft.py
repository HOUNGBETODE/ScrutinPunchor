from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging


class LoggingEventHandler(FileSystemEventHandler):
    """Custom handler for file system events"""

    def __init__(self, logger):
        self.logger = logger

        self.created_files = 0
        self.deleted_files = 0
        self.modified_files = 0
        self.permission_changes = 0

    def on_created(self, event):
        what = "directory" if event.is_directory else "file"
        # Get details about the created event
        # print(event.dest_path)
        # print(event.event_type)
        # print(event.is_directory)
        # print(event.is_synthetic)
        # print(event.src_path)
        path = event.src_path
        self.logger.info(f" {event}")

    def on_deleted(self, event):
        self.logger.info(f" {event}")

    def on_moved(self, event):
        self.logger.info(f" {event}")

    def on_modified(self, event):
        self.logger.info(f" {event}")

    def on_closed(self, event):
        self.logger.info(f" {event}")

logger = logging.getLogger(" @_ScrutinPunchor_@ ")

# formatting logs output
# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s - %(name)s - %(process)d - %(processName)s - %(message)s", 
#     datefmt="%Y-%m-%d %H:%M:%S"
# )

# displaying log messages into a file
file_handler = logging.FileHandler(
    "controllers/app.log", 
    mode="a", 
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - %(process)d - %(processName)s - %(message)s", 
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(ch)

event_handler = LoggingEventHandler(logger)

# creating the observer and scheduling the event handler
observer = Observer()
observer.schedule(
    event_handler, 
    path=r"E:\__stage__\endProject\app\TESTDIR", 
    recursive=True
)

observer.start()
try:
    while True:
        logging.info("Observer running...")
        observer.join(timeout=1)  # checking for new events periodically
except KeyboardInterrupt:
    observer.stop()

observer.join()


"""
def on_modified(self, event):
        if event.is_directory:
            return None  # Skip directories

        # Get the current modification time
        current_time = os.stat(event.src_path).st_mtime

        # Check if the file was previously modified (timestamp exists)
        if event.src_path in self.file_timestamps:
            previous_time = self.file_timestamps[event.src_path]
            if current_time != previous_time:
                self.logger.info(f"File modified: {event.src_path}")
                self.file_timestamps[event.src_path] = current_time  # Update timestamp
        else:
            # Store the modification time for the first time
            self.file_timestamps[event.src_path] = current_time
"""