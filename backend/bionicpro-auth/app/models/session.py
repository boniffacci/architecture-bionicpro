from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from typing import Dict, Any

class UserInfo(BaseModel):
    id: str = ""
    username: str = ""
    email: str = ""
    roles: List[str] = []
    user_id: int = 0
    crm_user_id: Optional[int] = None

class Session(BaseModel):
    id: str
    auth_code: str
    access_token: str
    refresh_token: str
    expires_at: datetime
    user_info: UserInfo
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str

class LoginRequest(BaseModel):
    code: str
    state: Optional[str] = None