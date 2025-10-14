import requests
import json

def rerank_pairs(pairs, url = "http://192.168.8.125:18801/rerank",):

    headers = {"Content-Type": "application/json"}
    payload = {
        "pairs": pairs
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        return response.json().get('scores')
    else:
        return {"error": response.status_code, "message": response.text}
