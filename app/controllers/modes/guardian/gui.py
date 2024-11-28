from typing import Any
from storage import ftp
from time import perf_counter as pc
import os, filehash, logging, shutil
from datetime import datetime
from controllers.utils import read_from_file_table
from models.database import LogEvent
from watchdog.observers import Observer
from concurrent.futures import ThreadPoolExecutor
from controllers.mdp import check_user_identity_on_confirm_box
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from controllers.utils import (
    from_SP, out_SP, logFileSystemEvent, notify, setPact, throw_action, inform,
    extract_patterns_from_file_table, save_to_file_table
)

def init_checking_G_gui(folder, user_id):
    previous_state = extract_patterns_from_file_table(folder)
    previous_state_keys = list(previous_state.keys())

    def checker(tuple_arg):
        folder_path = tuple_arg[0].replace("\\", "/")
        for file in tuple_arg[2]:
            full_file_path = f"{folder_path}/{file}"
            if full_file_path in previous_state_keys:
                filesha512hash = filehash.FileHash("sha512").hash_file(full_file_path)
                if filesha512hash != previous_state[full_file_path]:
                    message = f"{full_file_path } has been modified quite a long time. Are you the one behind it ?"
                    notify(message)
                    if not throw_action(message):
                        os.remove(full_file_path)
                        ftp.ftp_get(full_file_path, user_id)
                    else:
                        save_to_file_table(full_file_path, filesha512hash)
                        ftp.ftp_put(full_file_path, user_id)
            else:
                filesha512hash = filehash.FileHash("sha512").hash_file(full_file_path)
                save_to_file_table(full_file_path, filesha512hash)
                ftp.ftp_put(full_file_path, user_id)

    with ThreadPoolExecutor(os.cpu_count()) as executor:
        executor.map(checker, os.walk(folder))


def action_on_create(created_file_type, created_file_path, user_id):
    if not throw_action(f"{created_file_path} has just been created. Does such event come from you ?"):
        if check_user_identity_on_confirm_box():
            setPact(
                event = LogEvent.DELETED, 
                file_type = created_file_type, 
                source = created_file_path, 
                user_id = user_id
            )
            if created_file_type == "folder":
                for tuple_choices in list(os.walk(created_file_path)):
                    for file in tuple_choices[-1]:
                        to_erase = tuple_choices[0] + os.path.sep + file
                        setPact(
                            event = LogEvent.DELETED, 
                            file_type = "file", 
                            source = to_erase, 
                            user_id = user_id
                        )
                        os.remove(to_erase)
                os.rmdir(created_file_path)
            elif created_file_type == "file":
                os.remove(created_file_path)
    else:
        if check_user_identity_on_confirm_box():
            if created_file_type == "file":
                filesha512hash = filehash.FileHash("sha512").hash_file(created_file_path)
                save_to_file_table(created_file_path, filesha512hash)
            ftp.ftp_put(created_file_path, user_id)


def action_on_modify(modified_file_type, modified_file_path, user_id):
    if not throw_action(f"{modified_file_path} has just been modified. Does such event come from you ?"):
        if check_user_identity_on_confirm_box():
            setPact(
                event = LogEvent.DELETED, 
                file_type = modified_file_type, 
                source = modified_file_path, 
                user_id = user_id
            )
            os.remove(modified_file_path)
            ftp.ftp_get(modified_file_path, user_id)
    else:
        if check_user_identity_on_confirm_box():
            filesha512hash = filehash.FileHash("sha512").hash_file(modified_file_path)
            save_to_file_table(modified_file_path, filesha512hash)
            ftp.ftp_put(modified_file_path, user_id)


def action_on_move(moved_file_type, old_file_path, new_file_path, user_id):
    if not throw_action(f"{old_file_path} has just been moved to {new_file_path}. Does such event come from you ?"):
        if check_user_identity_on_confirm_box():
            setPact(
                event = LogEvent.MOVED, 
                file_type = moved_file_type, 
                source = new_file_path,
                destination = old_file_path, 
                user_id = user_id
            )
            shutil.move(new_file_path, old_file_path)
    else:
        if check_user_identity_on_confirm_box():
            if moved_file_type == "file":
                save_to_file_table(moved_file_path, None, new_file_path)
            ftp.ftp_delete(old_file_path, user_id)
            ftp.ftp_put(new_file_path, user_id)


def action_on_delete(deleted_file_type, deleted_file_path, user_id):
    if not throw_action(f"{deleted_file_path} has just been deleted. Does such event come from you ?"):
        if check_user_identity_on_confirm_box():
            setPact(
                event = LogEvent.CREATED, 
                file_type = deleted_file_type, 
                source = deleted_file_path,
                user_id = user_id
            )
            ftp.ftp_get(deleted_file_path, user_id)
    else:
        if check_user_identity_on_confirm_box():
            mark_as_deleted(deleted_file_path)
            ftp.ftp_delete(deleted_file_path, user_id)



class _DuplicateEventLimiter:

    _DUPLICATE_THRESOLD: float = 30

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
        what = "directory" if event.is_directory else "file"
        source = event.src_path.replace("\\", "/") or ""
        destination = event.dest_path.replace("\\", "/") or ""
        event_ = LogEvent.CREATED if event.event_type == "created" else LogEvent.MODIFIED if event.event_type == "modified" else None
        logFileSystemEvent(event = event_, file_type = what, source = source, destination = destination, user_id = self.user_id)
        
        match event.event_type:
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
                else:
                    out_SP(
                        event = LogEvent.CREATED, 
                        file_type = what,
                        source = source, 
                        user_id = self.user_id
                    )
            case "modified":
                x = pc()
                filesha512hash = filehash.FileHash("sha512").hash_file(source)
                if ((not self._is_duplicate(event)) and (read_from_file_table(source) != filesha512hash)):
                    # cmds = ["copy con", <and everytime something happens inside a folder>]
                    if not from_SP(
                        event = LogEvent.MODIFIED, 
                        file_type = what,
                        source = source, 
                        user_id = self.user_id
                    ):
                        if what == "file":
                            self.alert(f" Modified {what} : {source}")
                            action_on_modify(
                                modified_file_type=what,
                                modified_file_path=source,
                                user_id=self.user_id
                            )
                    else:
                        out_SP(
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
                else:
                    out_SP(
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
                else:
                    out_SP(
                        event = LogEvent.DELETED,
                        file_type = what,
                        source = source,
                        user_id = self.user_id
                    )


def guard(folder_path, user_id, user_pseudo, user_email):
    logger = logging.getLogger(' @_ScrutinPunchor_@ ')
    logger.setLevel(logging.DEBUG)

    init_checking_G_gui(folder_path, user_id)
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