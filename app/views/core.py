import os, platform, threading, time
# from controllers.modes import consumer
from concurrent.futures import ThreadPoolExecutor
from controllers.utils import banner, core_info, prompt, validate_folder, validate_hids_mode


guard_ = watch_ = cli_ = None
if platform.system() == "Linux":
    if os.environ.get("DISPLAY") in (":0", None):
        from controllers.modes.guardian.cli import guard
        from controllers.modes.watcher.cli import watch
        guard_, watch_, cli_ = guard, watch, True
else:
    from controllers.modes.guardian.gui import guard
    from controllers.modes.watcher.gui import watch
    guard_, watch_ = guard, watch


def show(user_id : int, user_pseudo : str, user_email : str):
    """ Deals with ScrutinPunchor main view """

    banner()
    core_info()

    # load consumer in case of cli_ environment found
    # if cli_:
    #     # create a thread so as to execute the heavy task
    #     thread = threading.Thread(target=consumer.consume, args=(user_pseudo,))
    #     thread.start()

    with ThreadPoolExecutor() as executor:
        running_tasks = {}

        while True:
            user_input = prompt("Folder plus mode : ")
            user_input_hash_splitted = user_input.split("#")
            user_input_folder = "#".join(user_input_hash_splitted[:-1])
            user_input_mode = "" if len(user_input_hash_splitted) == 1 else user_input_hash_splitted[-1]
            
            if validate_folder(user_input_folder) and validate_hids_mode(user_input_mode):
                if user_input_mode == "GUARDIAN":
                    task = executor.submit(guard_, user_input_folder, user_id, user_pseudo, user_email)
                    running_tasks[task] = user_input
                elif user_input_mode == "WATCHER":
                    task = executor.submit(watch_, user_input_folder, user_id, user_email)
                    running_tasks[task] = user_input
            
            for task in list(running_tasks.keys()):
                if task.done():
                    running_tasks.pop(task)