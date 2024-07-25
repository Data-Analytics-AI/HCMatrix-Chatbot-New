
import requests
import json

def chat_endpoint(user_query, employee_metadata, audio):

    url = "http://0.0.0.0:5500/chat"

    payload = json.dumps({
        "user_query": f"{user_query}",
        "audio": audio,
        "employee_metadata": employee_metadata
    })

    headers = {'Content-Type': 'application/json'}

    response = requests.request("POST", url, headers=headers, data=payload)
    json_resp = response.json()
    return json_resp