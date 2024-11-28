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
    from_SP, out_SP, logFileSystemEvent, notify, setPact, throw_action, inform, send_mail, 
    obfuscate_data, send_message_to_slack, read_from_file_table
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

    def __init__(self, logger, user_id, user_pseudo, user_email):
        self.logger = logger or logging.root
        self.user_id = user_id
        self.user_pseudo = user_pseudo
        self.user_email = user_email
        if not self.user_id:
            exit()
        _DuplicateEventLimiter.__init__(self)

    def on_any_event(self, event):
        what = "directory" if event.is_directory else "file"
        source = event.src_path.replace("\\", "/")
        destination = event.dest_path.replace("\\", "/") or ""
        event_name = event.event_type
        event_log_type = LogEvent.CREATED if event_name == "created" else LogEvent.MODIFIED if event_name == "modified" else LogEvent.MOVED if event_name == "moved" else LogEvent.DELETED
        
        if (event_name in ("created", "moved", "deleted")) or (
            (event_name == "modified") 
            and 
            (not self._is_duplicate(event))
            and
            (read_from_file_table(source) != filehash.FileHash("sha512").hash_file(source))
        ):
            x = pc()
            if not from_SP( event = event_log_type, file_type = what, source = source, destination = destination, user_id = self.user_id ):
                message = f" Created {what} : {source}" if event_name == "created" else f" Modified {what} : {source}" if event_name == "modified" else f" Moved {what} : from {source} to {destination}" if event_name == "moved" else f" Deleted {what} : {source}"
                message += ". Check your mail in order to react."
                send_message_to_slack(message)
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
            else:
                out_SP( event = event_log_type, file_type = what, source = source, destination = destination, user_id = self.user_id )
            inform(pc() - x)
        logFileSystemEvent(
            event = event_log_type,
            source = source,
            user_id = self.user_id,
            file_type = what, 
            destination = destination 
        )


def guard(folder_path, user_id, user_pseudo, user_email):
    logger = logging.getLogger(' @_ScrutinPunchor_@ ')
    logger.setLevel(logging.DEBUG)

    # init_checking_G_cli(folder_path, user_id, user_pseudo, user_email)
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

    observer = Observer()
    observer.schedule(
        event_handler, 
        path = folder_path, 
        recursive = True
    )

    observer.start()
    try:
        while True:
            observer.join(timeout = 1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()