
from cosmos_service import CosmosClient

with CosmosClient(database_name="hcm-chatbot", collection_name="user-chat") as client:
    data  = {'employee_metadata': {'department_id': '43', 'role_id': '323', 'group_id': '54', 'company_id': '53', 'id': '372'}, 'question': 'What projects are assigned to me?', 'answer': "The `onboardings_task` table contains onboarding task information but does not directly link employees to projects.\n\nGiven the absence of a direct linking table for projects and employees, it is possible that project assignments might be part of a custom workflow or managed through another system not directly reflected in the current database structure.\n\nBased on the available data, I can't determine which projects are assigned to employee ID 372. \n\nIf you have access to additional systems or records, you might want to consult those for specific project assignments.", 'timestamp': '2024-08-09 14:22:36', 'audio': 'http://127.0.0.1:5500/download_audio/?file=response_audio_b2910525-9684-45da-a9cc-0cc78fb759b8.wav', 'request_id': 'b2910525-9684-45da-a9cc-0cc78fb759b8', 'chat_id': '234trgftr'}
    # client.insert_one(data)
    # print (client.fetch_one({"chat_id": "234trgftr"}))
    query = {
        "chat_id": "234trgftr",
        "employee_metadata.id": "372",
        "employee_metadata.company_id": "53"
    }
    p = client.fetch_many(query)
    for i in p:
        print (i)

