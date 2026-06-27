# HCMatrix Chatbot Local Testing Guide

Welcome to the HCMatrix Chatbot testing environment! This guide explains how to get the application running locally so you can test the AI SQL Agent.

## 1. Prerequisite
- Python 3.10+
- Git Bash or any terminal

## 2. Setup Your Environment Variables
For security reasons, database credentials and OpenAI keys are **never** committed to GitHub.
1. In the root directory, you will see a file named `.env.example`.
2. Copy this file and rename it to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` in your code editor.
4. Reach out to the Lead Developer to get the exact values for the database connections and Azure OpenAI API keys, and paste them into your `.env` file.

## 3. Install Dependencies
Ensure you are using a virtual environment (optional but recommended), then install the required Python packages:
```bash
pip install -r requirements.txt
```

## 4. Run the Server
Start the local FastAPI server using Uvicorn:
```bash
python main.py
```
You should see:
`Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)`

## 5. Test the Chatbot
You can test the chatbot by opening a second terminal (Git Bash) and sending a `POST` request. 

### Basic Query
```bash
curl -X POST http://localhost:5000/chat -H "Content-Type: application/json" -d "{\"user_query\": \"What is my leave balance?\", \"chat_id\": \"test-01\", \"employee_metadata\": {\"department_id\": \"135\", \"role_id\": \"3\", \"group_id\": \"0\", \"company_id\": \"1\", \"id\": \"1221\"}}"
```

### Complex Query (Testing the SQL Agent)
```bash
curl -X POST http://localhost:5000/chat -H "Content-Type: application/json" -d "{\"user_query\": \"Who is my current line manager, what is their job title, and what department do they work in?\", \"chat_id\": \"test-complex-01\", \"employee_metadata\": {\"department_id\": \"135\", \"role_id\": \"3\", \"group_id\": \"0\", \"company_id\": \"1\", \"id\": \"1221\"}}"
```

## Troubleshooting
- **Missing Credentials?** Ensure your `.env` file is in the exact same directory as `main.py` and that the keys are not wrapped in quotes.
- **SQL Agent failing?** Ensure you are connected to the VPN (if applicable) and that the Azure MySQL Database firewall is whitelisting your current IP address.
