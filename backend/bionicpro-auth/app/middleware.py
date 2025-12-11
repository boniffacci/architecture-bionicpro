from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime
from app.services.session_service import SessionService

class AuthMiddleware:
    def __init__(self, session_service: SessionService):
        self.session_service = session_service
    
    def require_auth(self):
        async def middleware(request: Request):
            session_id = request.cookies.get("session_id")
            if not session_id:
                raise HTTPException(status_code=401, detail="No session found")
            
            session = self.session_service.get_session(session_id)
            if not session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            if datetime.now() > session.expires_at:
                raise HTTPException(status_code=401, detail="Session expired")
            
            request.state.session = session
            return None
        
        return middleware
    
    def require_session_rotation(self):
        async def middleware(request: Request):
            session_id = request.cookies.get("session_id")
            if not session_id:
                raise HTTPException(status_code=401, detail="No session found")
            
            session = self.session_service.get_session(session_id)
            if not session:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            if datetime.now() > session.expires_at:
                raise HTTPException(status_code=401, detail="Session expired")
            
            new_session = self.session_service.rotate_session(session_id)
            if not new_session:
                raise HTTPException(status_code=500, detail="Failed to rotate session")
            
            # Установим куку в response позже
            request.state.new_session_id = new_session.id
            request.state.session = new_session
            return None
        
        return middleware