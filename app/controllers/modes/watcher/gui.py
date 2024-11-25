import logging, os
from datetime import datetime
from models.database import LogEvent
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
from analyzers import malwareHashRegistry, quickSand, virusTotal
from controllers.utils import notify, from_SP, throw_action, logFileSystemEvent, convert_html_to_pdf, send_mail, inform

def vuln_detection(file_path):
    start_html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>ScrutinPunchor Analysis Report</title><style>body {"{background-image: url('https://th.bing.com/th/id/OIP.iXVOir0nPhfx2dyTWeCz3gHaE-?w=600&h=403&rs=1&pid=ImgDetMain'); background-size: cover; background-position: center; /* background-repeat: no-repeat; */ background-color: #f4f4f4; font-family: Arial, sans-serif; margin: 0; padding: 20px;}"}.container {"{background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); padding: 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;}"}</style></head><body><div class="container" style="background-color: burlywood;"><h1 style="text-align: center;">DETECTION ENGINE RESULTS AGAINST <span style="color: red;">{file_path.upper()}</span><h1></div><div class="container"><div><pre style="color: green;">
                ____                  _                      ____                   _ 
                / ___|  ___ _ __ _   _| |_(_)_ __            |  _ \\ _   _ _ __   ___| |__   ___  _ __
                \\___ \\ / __| '__| | | | __| | '_ \\           | |_) | | | | '_ \\ / __| '_ \\ / _ \\| '__|
                ___) | (__| |  | |_| | |_| | | | |           |  __/| |_| | | | | (__| | | | (_) | |
               |____/ \\___|_|   \\__,_|\\__|_|_| |_|           |_|    \\__,_|_| |_|\\___|_| |_|\\___/|_|</pre></div></div><div class="container" style="background-color: burlywood;"><p>"""
    end_html_content =  "</p></div></body></html>"

    results = {}
    with ThreadPoolExecutor() as executor:
        # To keep track of running tasks
        running_tasks = {
            executor.submit(virusTotal.analysis, file_path): "VirusTotalEngine",
            executor.submit(quickSand.analysis, file_path): "QuickSandEngine",
            executor.submit(malwareHashRegistry.analysis, file_path): "MalwareHashRegistryEngine"
        }

        for task in as_completed(running_tasks):
            service_name = running_tasks[task]
            inform(f"{service_name} was analyzing {file_path}...")
            try:
                result = task.result()
                results[service_name] = result
            except Exception as e:
                results[service_name] = f"Error: {str(e)}"
    # print(results)
    result_values = list(results.values())
    if any(list(result_values)):
        # print(list(result_values))
        inform(f"file {file_path} was suspected as nefarious.")
        mid_html_content_list = list(filter(lambda analysis : analysis is not None, result_values))
        notify(
            title="SCRUTIN-PUNCHOR",
            message=f"File {file_path} appears to be suspicious.\nActions need to be taken.",
            audio_file="media/intruder.wav",
            icon_file="media/alert.png"
        )
        pdf_path=f"reports/s{str(datetime.now().timestamp()).replace('.', '')}p.pdf"
        convert_html_to_pdf(
            html_string=start_html_content + "<hr/>".join(mid_html_content_list) + end_html_content,
            pdf_path=pdf_path
        )
        # send attack report to user
        send_mail("moberenge@gmail.com",
                    "Alert Report",
                "REPORT",
            {
                pdf_path: pdf_path
            }
        )
    return results

# vuln_detection(r"C:\Users\HP\Downloads\russian_roulette.zip")
# vuln_detection(r"E:\__stage__\endProject\app\malicious\windows_defender_deactivation_trial\dist\script.exe")


def vuln_assess_on_loading(folder):
    # declaring a function to asssess all files inside a directory
    def treatNassess(tuple_arg):
        folder = tuple_arg[0].replace("\\", "/")
        for file in tuple_arg[2]:
            vuln_detection(f"{folder}/{file}")
    # running the script with parallel tasks so as to speed the assess
    with ThreadPoolExecutor(os.cpu_count()) as executor:
        executor.map(treatNassess, os.walk(folder))


class WLoggingEventHandler(FileSystemEventHandler):
    """Custom handler for file system events"""

    def __init__(self, logger, user_id):
        self.logger = logger or logging.root
        self.user_id = user_id
        if not self.user_id:
            exit()

    def on_any_event(self, event):
        current_datetime = datetime.now().strftime("%a %Y-%m-%d %H:%M:%S")
        # ['dest_path', 'event_type', 'is_directory', 'is_synthetic', 'src_path']
        what = "directory" if event.is_directory else "file"
        source = event.src_path.replace("\\", "/")
        destination = event.dest_path
        event_ = LogEvent.CREATED if event.event_type == "created" else LogEvent.MODIFIED if event.event_type == "modified" else None
        
        if (event.event_type in ["created", "modified"]) and (what != "directory"):
            logFileSystemEvent(event = event_, file_type = what, source = source, destination = destination, user_id = self.user_id)
            vuln_detection(source)


def watch(folder_path, user_id):
    # vuln_assess_on_loading(folder_path)

    # configuring the custom logger
    logger = logging.getLogger(' @_ScrutinPunchor_@ ')
    logger.setLevel(logging.DEBUG)

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

    event_handler = WLoggingEventHandler(logger, user_id)

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
