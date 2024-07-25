
import requests


def chat_endpoint(employee_metadata, user_query=None, audio_file=None):
    url = "http://0.0.0.0:5000/chat"

    payload = {
        "user_query": user_query,
        **employee_metadata
    }

    files = [
        ('audio',(audio_file.split("/")[-1].split(".")[0],open(audio_file, 'rb'),'audio/wav'))
    ] if audio_file else None

    response = requests.request("POST", url, data=payload, files=files)
    json_resp = response.json()
    return json_resp

if __name__ == "__main__":
    payload = {'department_id': '43',
        'role_id': '323',
        'group_id': '54',
        'company_id': '53',
        'id': '372'}
    
    print (chat_endpoint(payload, audio_file='/home/alijoe/Downloads/record.wav'))