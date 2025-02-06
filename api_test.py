import pytest
from fastapi.testclient import TestClient
from api.app import app
import uuid
import base64
from services.cosmos_service import CosmosClient
from unittest.mock import patch
import time
from module.utils import config


# Creating an instance of the API for testing.
client = TestClient(app)


def test_read_root():
    """
    Test the root endpoint to ensure that the API is active.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "HCMatrix Chatbot is up! Endpoints are `/chat` and `/chat-history`."
    }


def test_chatbot_db_storage(
    employee_id: int = 657, company_id: int = 1, chat_id: str = str(uuid.uuid4())
):
    """
    Ensure that responses from the API are properly logged in the MongoDB database.

    :param employee_id (int): The unique identifier for the employee.
    :param company_id (int): The unique identifier for the company.
    :param chat_id (str): The unique identifier for the chat session.
    """

    # Sending payload to the API
    sample_payload = {
        "user_query": "Please tell me who my line manager is.",
        "chat_id": chat_id,
        "audio": False,
        "employee_metadata": {
            "department_id": "4",
            "role_id": "12",
            "group_id": "2",
            "company_id": str(company_id),
            "id": str(employee_id),
        },
    }

    response = client.post("/chat", json=sample_payload).json()
    response.pop("audio", None)
    print(f"Response: {response}")

    # Fetching stored data from the database
    query = {
        "chat_id": chat_id,
        "employee_metadata.id": str(employee_id),
        "employee_metadata.company_id": str(company_id),
    }

    with CosmosClient(database_name="hcm-chatbot", collection_name="user-chat") as db:
        stored_response = db.fetch_one(query)
        del stored_response["_id"]
        print(f"Stored Response: {stored_response}")

    assert response == stored_response


def test_text_to_speech_synthesis():
    """
    Ensure that valid text input produces synthesized speech audio.
    """

    sample_payload = {
        "user_query": "Hello, how are you?",
        "chat_id": str(uuid.uuid4()),
        "audio": True,  # Enable speech synthesis
        "employee_metadata": {
            "department_id": "4",
            "role_id": "12",
            "group_id": "2",
            "company_id": "1",
            "id": "657",
        },
    }

    response = client.post("/chat", json=sample_payload)

    assert response.status_code == 200

    response_json = response.json()
    assert "audio" in response_json, "Audio key missing in response"

    # Verify that the audio data is a valid base64-encoded string
    try:
        base64.b64decode(response_json["audio"], validate=True)
    except Exception:
        assert False, "Invalid base64-encoded audio data"

    print(f"Audio Response Length: {len(response_json['audio'])} bytes")


def test_chatbot_empty_input():
    """
    Ensure the API returns an appropriate error message when user_query is empty.
    """

    sample_payload = {
        "user_query": "",  # Empty input
        "chat_id": str(uuid.uuid4()),
        "audio": False,
        "employee_metadata": {
            "department_id": "4",
            "role_id": "12",
            "group_id": "2",
            "company_id": "1",
            "id": "657",
        },
    }

    response = client.post("/chat", json=sample_payload)

    assert response.status_code == 400  # Expecting a Bad Request
    response_json = response.json()

    assert "detail" in response_json, "Missing error message in response"
    assert (
        response_json["detail"] == "User query cannot be empty"
    ), "Unexpected error message"


def test_handle_invalid_characters():
    """
    Ensure that the chatbot can handle special, accented, and non-ASCII characters in the input,
    and that audio is generated for the response.
    """

    # Test input with special, accented, and non-ASCII characters
    special_characters_input = {
        "user_query": "Hello! How are you today? 😀🤖🌍💬 Éxamplé üñîçødé 🦄",
        "chat_id": str(uuid.uuid4()),
        "audio": True,  # Enable audio generation
        "employee_metadata": {
            "department_id": "4",
            "role_id": "12",
            "group_id": "2",
            "company_id": "1",
            "id": "657",
        },
    }

    # Sending payload to the API
    response = client.post("/chat", json=special_characters_input)

    assert response.status_code == 200  # Check if the request was successful
    response_json = response.json()

    # Verify that the chatbot responds without error
    assert "answer" in response_json, "Answer key missing in response"
    assert isinstance(response_json["answer"], str), "Response is not a valid string"

    # Verify that the audio key exists and is a valid base64-encoded string
    assert "audio" in response_json, "Audio key missing in response"
    try:
        base64.b64decode(response_json["audio"], validate=True)
    except Exception:
        assert False, "Invalid base64-encoded audio data"

    print(f"Response: {response_json['answer']}")
    print(f"Audio Response Length: {len(response_json['audio'])} bytes")


def test_speech_synthesis_cancellation():
    """
    Ensure that the chatbot API works even if speech synthesis fails.
    It should return a valid response with an empty string for 'audio'.
    """

    sample_payload = {
        "user_query": "Hello, please cancel my request.",
        "chat_id": str(uuid.uuid4()),
        "audio": True,  # Enable speech synthesis
        "employee_metadata": {
            "department_id": "4",
            "role_id": "12",
            "group_id": "2",
            "company_id": "1",
            "id": "657",
        },
    }

    # Mock Azure speech synthesis failure (simulate an exception)
    with patch(
        "module.spk.SpeechSynthesizerWrapper.synthesize",
        side_effect=Exception("Speech synthesis request canceled"),
    ):
        response = client.post("/chat", json=sample_payload)

    assert response.status_code == 200  # API should still function correctly
    response_json = response.json()

    assert "audio" in response_json, "Missing 'audio' key in response"
    assert (
        response_json["audio"] == ""
    ), "Audio should be empty string if synthesis fails"
    assert "answer" in response_json, "Chatbot response missing"


def test_invalid_request_format():
    """
    Ensure that the API returns a 422 error when the request payload is missing required fields.
    """
    invalid_payload = {  # Missing 'user_query'
        "chat_id": str(uuid.uuid4()),
        "audio": True,
        "employee_metadata": {
            "department_id": "4",
            "role_id": "12",
            "group_id": "2",
            "company_id": "1",
            "id": "657",
        },
    }

    response = client.post("/chat", json=invalid_payload)

    assert response.status_code == 422, "Expected 422 Unprocessable Entity"


def test_response_time(benchmark):
    """
    Benchmark the chatbot API's response time.
    Takes into account expected response times of dependencies:
    - Microsoft Speech Service TTS (~1s, but can be higher)
    - Azure OpenAI GPT-4o (~94ms per token, ~9.4s for 100 tokens)
    """

    payload = {
        "user_query": "Hello, how are you?",
        "chat_id": str(uuid.uuid4()),
        "audio": True,
        "employee_metadata": {
            "department_id": "4",
            "role_id": "12",
            "group_id": "2",
            "company_id": "1",
            "id": "657",
        },
    }

    # Benchmark the API call and capture execution time
    def api_call():
        start_time = time.time()
        response = client.post("/chat", json=payload)
        end_time = time.time()

        assert (
            response.status_code == 200
        ), f"Unexpected status code: {response.status_code}"

        return end_time - start_time  # Return execution time

    execution_time = benchmark.pedantic(
        api_call, iterations=1, rounds=10, warmup_rounds=1
    )

    expected_max_time = 5  # Buffer for TTS + GPT-4o response time
    assert (
        execution_time <= expected_max_time
    ), f"Response took too long: {execution_time:.2f}s"


# Run the tests with pytest
if __name__ == "__main__":
    pytest.main()
