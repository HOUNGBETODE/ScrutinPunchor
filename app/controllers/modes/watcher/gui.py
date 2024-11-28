import logging, os
from datetime import datetime
from models.database import LogEvent, Alert
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
from analyzers import malwareHashRegistry, quickSand, virusTotal
from controllers.utils import create, notify, from_SP, throw_action, logFileSystemEvent, convert_html_to_pdf, send_mail, inform

def vuln_detection(file_path, user_email, log_id):
    start_html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>ScrutinPunchor Analysis Report</title><style>body {"{background-image: url('https://th.bing.com/th/id/OIP.iXVOir0nPhfx2dyTWeCz3gHaE-?w=600&h=403&rs=1&pid=ImgDetMain'); background-size: cover; background-position: center; /* background-repeat: no-repeat; */ background-color: #f4f4f4; font-family: Arial, sans-serif; margin: 0; padding: 20px;}"}.container {"{background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); padding: 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;}"}</style></head><body><div class="container" style="background-color: burlywood;"><h1 style="text-align: center;">DETECTION ENGINE RESULTS AGAINST <span style="color: red;">{file_path.upper()}</span><h1></div><div class="container"><div><pre style="color: green;">
                ____                  _                      ____                   _ 
                / ___|  ___ _ __ _   _| |_(_)_ __            |  _ \\ _   _ _ __   ___| |__   ___  _ __
                \\___ \\ / __| '__| | | | __| | '_ \\           | |_) | | | | '_ \\ / __| '_ \\ / _ \\| '__|
                ___) | (__| |  | |_| | |_| | | | |           |  __/| |_| | | | | (__| | | | (_) | |
               |____/ \\___|_|   \\__,_|\\__|_|_| |_|           |_|    \\__,_|_| |_|\\___|_| |_|\\___/|_|</pre></div></div><div class="container" style="background-color: burlywood;"><p>"""
    end_html_content =  "</p></div></body></html>"

    results = {}
    with ThreadPoolExecutor() as executor:
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
    result_values = list(results.values())
    if any(list(result_values)):
        inform(f"file {file_path} was suspected as nefarious.")
        mid_html_content_list = list(filter(lambda analysis : analysis is not None, result_values))
        notify(
            title="SCRUTIN-PUNCHOR",
            message=f"File {file_path} appears to be suspicious.\nActions need to be taken.",
            audio_file="media/intruder.wav",
            icon_file="media/alert.png"
        )
        pdf_path=f"reports/s{str(datetime.now().timestamp()).replace('.', '')}p.pdf"
        report_body = start_html_content + "<hr/>".join(mid_html_content_list) + end_html_content
        convert_html_to_pdf(
            html_string=report_body,
            pdf_path=pdf_path
        )
        send_mail(user_email,
                    "Alert Report",
                "REPORT",
            {
                pdf_path: pdf_path
            }
        )

        create(Alert, analysis_result = report_body, log_id = log_id)
    return results

def vuln_assess_on_loading(folder):
    def treatNassess(tuple_arg):
        folder = tuple_arg[0].replace("\\", "/")
        for file in tuple_arg[2]:
            vuln_detection(f"{folder}/{file}")
    with ThreadPoolExecutor(os.cpu_count()) as executor:
        executor.map(treatNassess, os.walk(folder))


class WLoggingEventHandler(FileSystemEventHandler):
    """Custom handler for file system events"""

    def __init__(self, logger, user_id, user_email):
        self.logger = logger or logging.root
        self.user_id = user_id
        self.user_email = user_email
        if not self.user_id:
            exit()

    def on_any_event(self, event):
        current_datetime = datetime.now().strftime("%a %Y-%m-%d %H:%M:%S")
        what = "directory" if event.is_directory else "file"
        source = event.src_path.replace("\\", "/")
        destination = event.dest_path
        event_ = LogEvent.CREATED if event.event_type == "created" else LogEvent.MODIFIED if event.event_type == "modified" else None
        
        if (event.event_type in ["created", "modified"]) and (what != "directory"):
            log_id = logFileSystemEvent(event = event_, file_type = what, source = source, destination = destination, user_id = self.user_id)
            vuln_detection(source, self.user_email, log_id)


def watch(folder_path, user_id, user_email):
    # vuln_assess_on_loading(folder_path)

    logger = logging.getLogger(' @_ScrutinPunchor_@ ')
    logger.setLevel(logging.DEBUG)

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

    event_handler = WLoggingEventHandler(logger, user_id, user_email)

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