
from pydantic import BaseModel
from typing import *

class ChatSchema(BaseModel):
    user_query: str
    employee_metadata: Dict[str, Any]
