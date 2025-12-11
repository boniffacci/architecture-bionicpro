import secrets
from datetime import datetime, timedelta
from typing import Optional
from app.models.session import Session
from app.services.redis_service import RedisClient
from app.services.keycloak_service import KeycloakService

class SessionService:
    def __init__(self):
        self.redis = RedisClient()
        self.keycloak = KeycloakService()
    
    def create_session(self, code: str, redirect_uri: str) -> Optional[Session]:
        token_resp = self.keycloak.exchange_code_for_token(code, redirect_uri)
        if not token_resp:
            return None
        
        user_info = self.keycloak.get_user_info(token_resp.access_token)
        if not user_info:
            return None
        
        session_id = self._generate_session_id()
        expires_at = datetime.now() + timedelta(seconds=token_resp.expires_in)
        
        session = Session(
            id=session_id,
            auth_code=code,
            access_token=token_resp.access_token,
            refresh_token=token_resp.refresh_token,
            expires_at=expires_at,
            user_info=user_info,
            created_at=datetime.now()
        )
        
        if self.redis.set_session(session):
            return session
        
        return None
    
    def get_session(self, session_id: str) -> Optional[Session]:
        return self.redis.get_session(session_id)
    
    def get_session_by_code(self, code: str) -> Optional[Session]:
        return self.redis.get_session_by_code(code)
    
    def refresh_session(self, session_id: str) -> Optional[Session]:
        session = self.redis.get_session(session_id)
        if not session:
            return None
        
        # Если до истечения больше 30 секунд, возвращаем текущую
        if session.expires_at > datetime.now() + timedelta(seconds=30):
            return session
        
        token_resp = self.keycloak.refresh_token(session.refresh_token)
        if not token_resp:
            return None
        
        user_info = self.keycloak.get_user_info(token_resp.access_token)
        if not user_info:
            return None
        
        session.access_token = token_resp.access_token
        session.refresh_token = token_resp.refresh_token
        session.expires_at = datetime.now() + timedelta(seconds=token_resp.expires_in)
        session.user_info = user_info
        
        if self.redis.set_session(session):
            return session
        
        return None
    
    def rotate_session(self, session_id: str) -> Optional[Session]:
        session = self.redis.get_session(session_id)
        if not session:
            return None
        
        new_session_id = self._generate_session_id()
        
        new_session = Session(
            id=new_session_id,
            auth_code=session.auth_code,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at,
            user_info=session.user_info,
            created_at=datetime.now()
        )
        
        if self.redis.set_session(new_session):
            self.redis.delete_session(session_id)
            return new_session
        
        return None
    
    def delete_session(self, session_id: str) -> bool:
        return self.redis.delete_session(session_id)
    
    def _generate_session_id(self) -> str:
        return secrets.token_hex(16)