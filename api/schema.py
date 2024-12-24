from pydantic import BaseModel


class EmployeeMetadataSchema(BaseModel):
    department_id: str
    role_id: str
    group_id: str
    company_id: str
    id: str


class AudioChatSchema(BaseModel):
    user_query: str = None
    chat_id: str = None
    audio: bool = None
    employee_metadata: EmployeeMetadataSchema


class ChatSchema(BaseModel):
    user_query: str = None
    employee_metadata: EmployeeMetadataSchema


class ChatResponseSchema(BaseModel):
    employee_metadata: EmployeeMetadataSchema
    question: str
    answer: str
    audio_response: str = None
    timestamp: str
    request_id: str


class ChatHistory(BaseModel):
    chat_id: str
    employee_id: str
    company_id: str
