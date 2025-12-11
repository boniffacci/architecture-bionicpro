from pydantic import BaseModel
from typing import Optional, List

class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    roles: List[str] = []
    user_id: int
    crm_user_id: Optional[int] = None