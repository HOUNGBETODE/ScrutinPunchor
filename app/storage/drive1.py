# https://youtu.be/JwGzHitUVcU?si=P7HwJV3iVzKf6QNk
# https://developers.google.com/oauthplayground/?code=4/0AQlEd8xfTcjp7gz_pf5KVv4S8OjF0ADQZLTL6n49lqiMU07v73UuxzGiXnvrUoGC9rIN6A&scope=https://www.googleapis.com/auth/drive

import json
import requests
headers = {"Authorization": "Bearer ya29.a0AcM612zEHzDuVZxX1J_ji6wJ26PqHYj0epUc2MkzeO2-fYMPeb0tTeFw_RMzqHNOsD6xR11JyFuGpPdubkayj7qEIPQegqcrnWOr4jl9nQqySZ_qECjWxt_A29nNCetQ724y7XOgr4iyzjY10OuoYpq-yqNa6DbONBVn45TSaCgYKAf4SARISFQHGX2MiwIgezPThFgyGarEx1XjQ6g0175"}
para = {
    "name": "cahier_de_charges_du_memoire.pdf",
    "parents": ["<folder-ID>"]
}
files = {
    "data": ("metadata", json.dumps(para), "application/json; charset=UTF-8"),
    "file": open("./cahier_de_charges-2.pdf", "rb")
}
r = requests.post(
    "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
    headers = headers,
    files = files
)
print(r.text)

""" {
        "kind": "drive#file",
        "id": "1l0Xll7CIGzVrLqKOnoTSSXGVyK4QjLmr",
        "name": "cahier_de_charges_du_memoire.pdf",
        "mimeType": "application/pdf"
} """
