from typing import Any
from storage import ftp
from time import perf_counter as pc
import filehash, logging
from datetime import datetime
from controllers.utils import read_from_file_table
from models.database import LogEvent
from watchdog.observers import Observer
from concurrent.futures import ThreadPoolExecutor
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from controllers.utils import (
    from_SP, logFileSystemEvent, notify, setPact, throw_action, inform, 
    init_checking_G_gui, action_on_create, action_on_modify, action_on_move, action_on_delete
)



class _DuplicateEventLimiter:

    _DUPLICATE_THRESOLD: float = 15

    def __init__(self) -> None:
        self._last_event: dict[str, Any] = {
            "time": 0,
            "event": None
        }

    def _is_duplicate(self, event: FileSystemEvent) -> bool:
        is_duplicate = (
            pc() - self._last_event["time"] < self._DUPLICATE_THRESOLD
            and
            self._last_event["event"] == event
        )

        self._last_event = {
            "time": pc(),
            "event": event
        }

        return is_duplicate


class GLoggingEventHandler(FileSystemEventHandler, _DuplicateEventLimiter):
    """Custom handler for file system events"""

    # in spirit, moved = deleted + created + modified (if needed)
    #            copied = created + modified (if needed)

    def __init__(self, logger, user_id, user_pseudo, user_email):
        self.logger = logger or logging.root
        self.user_id = user_id
        self.user_pseudo = user_pseudo
        self.user_email = user_email
        if not self.user_id:
            exit()
        _DuplicateEventLimiter.__init__(self)

    def alert(self, message):
        self.logger.info(message)
        notify(message)

    def on_any_event(self, event):
        # current_datetime = datetime.now().strftime("%a %Y-%m-%d %H:%M:%S")
        # ['dest_path', 'event_type', 'is_directory', 'is_synthetic', 'src_path']
        what = "directory" if event.is_directory else "file"
        source = event.src_path.replace("\\", "/")
        destination = event.dest_path.replace("\\", "/")
        
        match event.event_type:
            # we do not need to deal with FileClosedEvent anymore, so case "closed" is not compulsory
            case "created":
                # cmds = ("copy NUL", "mkdir")
                if not from_SP(
                    event = LogEvent.CREATED, 
                    file_type = what,
                    source = source, 
                    user_id = self.user_id
                ):
                    self.alert(f" Created {what} : {source}")
                    action_on_create(
                        created_file_type=what,
                        created_file_path=source,
                        user_id=self.user_id
                    )
                logFileSystemEvent(
                    event = LogEvent.CREATED, 
                    file_type = what, 
                    source = source, 
                    user_id = self.user_id
                )
            case "modified":
                x = pc()
                filesha512hash = filehash.FileHash("sha512").hash_file(source)
                # print((read_from_file_table(source) != filesha512hash))
                # print((not self._is_duplicate(event)), (read_from_file_table(source) != filesha512hash))
                if (not self._is_duplicate(event)):
                    # cmds = ["copy con", <and everytime something happens inside a folder>]
                    # folders modififcation are very useless for us as information
                    # print("in")
                    if not from_SP(
                        event = LogEvent.MODIFIED, 
                        file_type = what,
                        source = source, 
                        user_id = self.user_id
                    ):
                        # message = f" Modified {what} : {source}"
                        # self.logger.info(message)
                        if what == "file":
                            self.alert(f" Modified {what} : {source}")
                            action_on_modify(
                                modified_file_type=what,
                                modified_file_path=source,
                                user_id=self.user_id
                            )
                    logFileSystemEvent(
                        event = LogEvent.MODIFIED, 
                        file_type = what, 
                        source = source, 
                        user_id = self.user_id
                    )
                inform(pc() - x)
            case "moved":
                # cmds = ("rename",)
                if not from_SP(
                    event = LogEvent.MOVED, 
                    file_type = what,
                    source = source, 
                    destination = destination, 
                    user_id = self.user_id
                ):
                    self.alert(f" Moved {what} : from {source} to {destination}")
                    action_on_move(
                        moved_file_type=what,
                        old_file_path=source,
                        new_file_path=destination,
                        user_id=self.user_id
                    )
                logFileSystemEvent(
                    event = LogEvent.MOVED, 
                    file_type = what, 
                    source = source, 
                    destination = destination, 
                    user_id = self.user_id
                )
            case "deleted":
                # cmds = ("del", "rmdir")
                if not from_SP(
                    event = LogEvent.DELETED,
                    file_type = what,
                    source = source,
                    user_id = self.user_id
                ):
                    self.alert(f" Deleted {what} : {source}")
                    action_on_delete(
                        deleted_file_type=what,
                        deleted_file_path=source,
                        user_id=self.user_id
                    )
                logFileSystemEvent(
                    event = LogEvent.DELETED, 
                    file_type = what, 
                    source = source, 
                    user_id = self.user_id
                )


def guard(folder_path, user_id, user_pseudo, user_email):
    # configuring the custom logger
    logger = logging.getLogger(' @_ScrutinPunchor_@ ')
    logger.setLevel(logging.DEBUG)

    init_checking_G_gui(folder_path, user_id)
    # inform(folder_path, user_id)
    # displaying log messages into a file
    file_handler = logging.FileHandler(
        "logs/app.log", 
        mode = "a", 
        encoding = "utf-8"
    )
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(message)s", 
        datefmt="%a %Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    event_handler = GLoggingEventHandler(logger, user_id, user_pseudo, user_email)

    # creating the observer and scheduling the event handler
    observer = Observer()
    observer.schedule(
        event_handler, 
        path = folder_path, 
        recursive = True
    )

    observer.start()
    try:
        while True:
            observer.join(timeout = 1)  # checking for new events periodically
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
