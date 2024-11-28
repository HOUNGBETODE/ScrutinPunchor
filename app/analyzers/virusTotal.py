from config import VT
import os, requests, time
from json2table import convert
from controllers.utils import notify


def analysis(FILE_PATH):
    diagnosis = None
    vt_api_creds = VT.load()
    session = requests.Session()
    url = "http://www.virustotal.com/api/v3/files/upload_url"
    session.headers = {vt_api_creds["name"]: vt_api_creds["value"]}
    files = {"file": open(os.path.abspath(FILE_PATH), "rb")}

    get_upload_url = session.get(url)
    upload_url = get_upload_url.json()["data"]

    file_upload = session.post(upload_url, files=files)
    file_upload_response = file_upload.json()
    report_url = file_upload_response["data"]["links"]["self"]

    retrieve_report = session.get(report_url)
    retrieve_report_response = retrieve_report.json()
    uploaded_file_consultable_url = retrieve_report_response["data"]["links"]["self"]
    uploaded_file_id = uploaded_file_consultable_url.split("/")[-1]

    report_statistics = retrieve_report_response["data"]["attributes"]["stats"]
    confirmed_timeout = report_statistics["confirmed-timeout"]
    type_unsupported = report_statistics["type-unsupported"]
    undetected = report_statistics["undetected"]
    suspicious = report_statistics["suspicious"]
    malicious = report_statistics["malicious"]
    harmless = report_statistics["harmless"]
    failure = report_statistics["failure"]
    timeout = report_statistics["timeout"]

    if malicious or suspicious:
        antiviruses_analysis = retrieve_report_response["data"]["attributes"]["results"]
        diagnosis = f"""
<b>**** VIRUSTOTAL ENGINE RESULTS ***</b>
<br />
To dig further, please consult <a href="{uploaded_file_consultable_url}">{uploaded_file_consultable_url}</a> providing your VirusTotal api key in request's headers.
<pre>Useful endpoints you can look at are :
                                        - /votes
                                        - /comments
                                        - /behaviours
                                        - /behaviour_summary
                                        - /behaviour_mitre_tree</pre>
Below is the antiviruses analysis results : {convert(antiviruses_analysis)}
"""

    session.close()
    return diagnosis