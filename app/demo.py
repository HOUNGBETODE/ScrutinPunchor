from config import VT
import os, vt

vt_api_creds = VT.load()
client = vt.Client(vt_api_creds["value"])
malicious_hash = "44d88612fea8a8f36de82e1278abb02f"

file = client.get_object(f"/files/{malicious_hash}")
print(file.last_analysis_stats)

os.chdir("G:/folder2")

try:
    with open("downloaded_file", "wb") as f:
        client.download_file(malicious_hash, f)
except vt.error.APIError as e:
    print(f"APIError occurred: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    client.close()
