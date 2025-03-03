from pydantic import BaseModel


class EmployeeMetadataSchema(BaseModel):
    department_id: str
    role_id: str
    group_id: str
    company_id: str
    id: str


class ChatInputSchema(BaseModel):
    user_query: str
    chat_id: str
    employee_metadata: EmployeeMetadataSchema


class ChatResponseSchema(BaseModel):
    employee_metadata: EmployeeMetadataSchema
    question: str
    answer: str
    timestamp: str
    request_id: str
    chat_id: str


class AudioInput(BaseModel):
    text: str


class ChatHistory(BaseModel):
    chat_id: str
    employee_id: str
    company_id: str
