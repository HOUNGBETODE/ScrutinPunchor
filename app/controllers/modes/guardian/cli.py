from typing import Any
from storage import ftp
from datetime import datetime
from time import perf_counter as pc
import filehash, logging, os, shutil
from models.database import LogEvent
from watchdog.observers import Observer
from concurrent.futures import ThreadPoolExecutor
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from controllers.utils import (
    from_SP, logFileSystemEvent, notify, setPact, throw_action, inform, send_mail, 
    obfuscate_data, send_message_to_slack, read_from_file_table, init_checking_G_cli
)




class _DuplicateEventLimiter:

    _DUPLICATE_THRESOLD: float = 9.5

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
    """ Custom handler for file system events """

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

    def on_any_event(self, event):
        # ['dest_path', 'event_type', 'is_directory', 'is_synthetic', 'src_path']
        what = "directory" if event.is_directory else "file"
        source = event.src_path.replace("\\", "/")
        destination = event.dest_path.replace("\\", "/")
        
        # created, modified, moved, deleted
        if (event.event_type in ("created", "moved", "deleted")) or (
            (event.event_type == "modified") 
            and 
            (not self._is_duplicate(event))
            and
            (read_from_file_table(source) != filehash.FileHash("sha512").hash_file(source))
        ):
            x = pc()
            event_name = event.event_type
            # logging event
            logFileSystemEvent(
                event = LogEvent.CREATED if event_name == "created" else LogEvent.MODIFIED if event_name == "modified" else LogEvent.MOVED if event_name == "moved" else LogEvent.DELETED, 
                source = source,
                user_id = self.user_id,
                file_type = what, 
                destination = destination 
            )
            # notify user via slack
            message = f" Created {what} : {source}" if event_name == "created" else f" Modified {what} : {source}" if event_name == "modified" else f" Moved {what} : from {source} to {destination}" if event_name == "moved" else f" Deleted {what} : {source}"
            message += ". Check your mail in order to react."
            print(message)
            send_message_to_slack(message)
            # send mail to concerned user so as to take actions
            send_mail(
                receiver_mail = self.user_email,
                message_subject = "User Awareness",
                message_type = "AWARENESS",
                message_body = {
                    "pseudo": self.user_pseudo,
                    "event": f"{what.capitalize()} {source} has just been {event_name} on your system." if event_name != "moved" else f"{what.capitalize()} {source} has just been moved to {destination} on your system.",
                    "data": obfuscate_data(
                        {
                            "scrutin-punchor-mode": "GUARDIAN",
                            "event": event_name,
                            "source": source,
                            "filetype": what,
                            "destination": destination,
                            "user_id": self.user_id,
                            "originate-timestamp": datetime.now().timestamp()
                        },
                        self.user_pseudo
                    )
                }
            )
            # inform user
            inform(pc() - x)


def guard(folder_path, user_id, user_pseudo, user_email):
    # configuring the custom logger
    logger = logging.getLogger(' @_ScrutinPunchor_@ ')
    logger.setLevel(logging.DEBUG)

    # init_checking_G_cli(folder_path, user_id, user_pseudo, user_email)
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
