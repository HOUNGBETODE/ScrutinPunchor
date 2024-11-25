from config import VT
import os, requests, time #, vt
from json2table import convert
from controllers.utils import notify


def analysis(FILE_PATH):
    # create a session for making requests to virus total api
    diagnosis = None
    vt_api_creds = VT.load()
    session = requests.Session()
    url = "http://www.virustotal.com/api/v3/files/upload_url"
    session.headers = {vt_api_creds["name"]: vt_api_creds["value"]}
    files = {"file": open(os.path.abspath(FILE_PATH), "rb")}

    # get an url for uploading a large file
    get_upload_url = session.get(url)
    upload_url = get_upload_url.json()["data"]

    # upload the file for analysis and retrieve the report url
    file_upload = session.post(upload_url, files=files)
    file_upload_response = file_upload.json()
    report_url = file_upload_response["data"]["links"]["self"]

    # examine the report about the file uploaded
    retrieve_report = session.get(report_url)
    retrieve_report_response = retrieve_report.json()
    # print(f"{retrieve_report_response = }")
    uploaded_file_consultable_url = retrieve_report_response["data"]["links"]["self"]
    uploaded_file_id = uploaded_file_consultable_url.split("/")[-1]

    # extract informations about analysis' stats
    report_statistics = retrieve_report_response["data"]["attributes"]["stats"]
    confirmed_timeout = report_statistics["confirmed-timeout"]
    type_unsupported = report_statistics["type-unsupported"]
    undetected = report_statistics["undetected"]
    suspicious = report_statistics["suspicious"]
    malicious = report_statistics["malicious"]
    harmless = report_statistics["harmless"]
    failure = report_statistics["failure"]
    timeout = report_statistics["timeout"]

    # Ex : uploaded_file_consultable_url = "http://www.virustotal.com/api/v3/files/07492af0257d8fcf232d099156b484ae2d3ecde7acf423a09ba403e15bc0d689"

    # generate a report about antiviruses which marked the file as malicious or suspicious
    if malicious or suspicious:
        antiviruses_analysis = retrieve_report_response["data"]["attributes"]["results"]
        # print(antiviruses_analysis)

        """ # fellow's comments about the malicious file
        get_comments = session.get(uploaded_file_consultable_url+"/comments")
        print(get_comments.json())

        # fellow's votes about the malicious file
        get_votes = session.get(uploaded_file_consultable_url+"/votes")
        print(get_votes.json())

        # get a summary about the uploaded file's behavioural information
        uploaded_file_behaviours = session.get(uploaded_file_consultable_url+"/behaviours")
        print(uploaded_file_behaviours.json()) """

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

        # /votes
        # /comments
        # /behaviours
        # /behaviour_summary
        # /behaviour_mitre_tree

    # closing the session
    session.close()
    return diagnosis






# def analysis(FILE_PATH):
#     diagnosis = None
#     files = {"file": open(os.path.abspath(FILE_PATH), "rb")}

#     vt_api_creds = VT.load()
#     client = vt.Client(vt_api_creds["value"])

#     diagnosis = f"""
# <b>**** VIRUSTOTAL ENGINE RESULTS ***</b>
# <br />
# To dig further, please consult <a href="{uploaded_file_consultable_url}">{uploaded_file_consultable_url}</a> providing your VirusTotal api key in request's headers.
# <pre>Useful endpoints you can look at are :
#                                         - /votes
#                                         - /comments
#                                         - /behaviours
#                                         - /behaviour_summary
#                                         - /behaviour_mitre_tree</pre>
# Below is the antiviruses analysis results : {convert(antiviruses_analysis)}
# """

#     # closing the session
#     client.close()
#     return diagnosis