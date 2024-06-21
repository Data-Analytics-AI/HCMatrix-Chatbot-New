
from pydantic import BaseModel
from typing import *

class ChatSchema(BaseModel):
    user_query: str
    query_type: Union[str]
    employee_metadata: Dict[str, Any]
