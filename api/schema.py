
from pydantic import BaseModel
from typing import *

class EmployeeMetadataSchema(BaseModel):
    departement_id: str
    role_id: str
    group_id: str
    company_id: str
    id: str

class ChatSchema(BaseModel):
    user_query: str
    employee_metadata: EmployeeMetadataSchema

class ChatResponseSchema(BaseModel):
    employee_metadata: EmployeeMetadataSchema
    question: str
    answer: str
    timestamp: str
    request_id: str