
import requests
import json

def chat_endpoint(user_query, employee_metadata):
    url = "http://0.0.0.0:5000/chat"

    # payload = json.dumps({
    #     "user_query": "kedu",
    #     "query_type": "general",
    #     "employee_metadata": {
    #         "user_departement_id": 43,
    #         "user_role_id": "323",
    #         "user_group_id": "54",
    #         "company_id": "53",
    #         "employee_id": "373"
    #     }
    #     })

    payload = json.dumps(
        {
            "user_query": user_query,
            # "query_type": query_type,
            "employee_metadata": employee_metadata
        }
    )
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    json_resp = response.json()
    return json_resp