from locust import HttpUser, task, between


class ChatbotUser(HttpUser):
    wait_time = between(1, 3)  # Simulate user wait time (1-3 sec) before making next request

    @task
    def send_chat_request(self):
        """Simulates a user sending a chat request."""
        payload = {
            "user_query": "Hello, who is my line manager?",
            "chat_id": "test-benchmark",
            "employee_metadata": {
                "department_id": "4",
                "role_id": "12",
                "group_id": "2",
                "company_id": "1",
                "id": "657",
            },
        }
        headers = {"Content-Type": "application/json"}
        response = self.client.post("/chat", json=payload, headers=headers, timeout=None)

        print(f"Locust Response Status Code: {response.status_code}")
        print(f"Locust Response Body: {response.text}")  # Check if it's a valid JSON response

        if response.status_code != 200:
            print(f"⚠️ Unexpected Status Code: {response.status_code} | Response: {response.text}")
