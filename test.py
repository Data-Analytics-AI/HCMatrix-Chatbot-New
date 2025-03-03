import pytest
from fastapi.testclient import TestClient
from api.app import app
import uuid
from module.cosmos_service import CosmosClient

# Creating an instance of the API for testing.
client = TestClient(app)


def test_read_root():
    """
    Test the root endpoint to ensure that the API is active.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "HCMatrix Chatbot is up! Endpoints are `/chat`, `/audio`, `/chat-history` and `all-chat-history`."
    }


def test_chatbot_db_storage():
    """
    Ensure that responses from the API are properly logged in the MongoDB database.
    """
    query = {
        "chat_id": '800624d8-51d4-44b9-9b49-6ee5bf440cd6',
        "employee_metadata.id": "657",
        "employee_metadata.company_id": "1",
    }
    expected_response = {
        'employee_metadata': {'department_id': '4', 'role_id': '12', 'group_id': '2', 'company_id': '1', 'id': '657'},
        'question': 'Please tell me who my line manager is.',
        'answer': "Your current line manager's ID is 116.",
        'timestamp': '2025-02-20 16:09:56',
        'request_id': 'a1abd5f0-fd35-460f-a931-5c95fb72db30',
        'chat_id': '800624d8-51d4-44b9-9b49-6ee5bf440cd6'}
    db = CosmosClient(database_name="hcm-chatbot", collection_name="user-chat")
    stored_response = db.fetch_one(query)
    del stored_response["_id"]
    print(f"Stored Response: {stored_response}")

    assert expected_response == stored_response


def test_chatbot_empty_input():
    """
    Ensure the API returns an appropriate error message when user_query is empty.
    """
    sample_payload = {
        "user_query": "",
        "chat_id": str(uuid.uuid4()),
        "employee_metadata": {
            "department_id": "4",
            "role_id": "12",
            "group_id": "2",
            "company_id": "1",
            "id": "657",
        },
    }

    response = client.post("/chat", json=sample_payload)

    assert response.status_code == 400
    response_json = response.json()
    assert "detail" in response_json
    assert response_json["detail"] == "User query cannot be empty"


def test_invalid_request_format():
    """
    Ensure that the API returns a 422 error when the request payload is missing required fields.
    """
    invalid_payload = {
        "chat_id": str(uuid.uuid4()),
        "employee_metadata": {
            "department_id": "4",
            "role_id": "12",
            "group_id": "2",
            "company_id": "1",
            "id": "657",
        },
    }

    response = client.post("/chat", json=invalid_payload)

    assert response.status_code == 422


def test_audio_synthesis():
    """
    Ensure the /audio endpoint generates a valid audio response.
    """
    response = client.post("/audio", json={"text": "Hello, how are you?"})

    assert response.status_code == 200
    assert isinstance(response.content, bytes)
    assert len(response.content) > 0


def test_audio_synthesis_empty_text():
    """
    Ensure the /audio endpoint returns a 400 error for empty text.
    """
    response = client.post("/audio", json={"text": ""})

    assert response.status_code == 400
    response_json = response.json()
    assert "detail" in response_json
    assert response_json["detail"] == "Text cannot be empty"


if __name__ == "__main__":
    pytest.main()
