import json
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from app.services.session_service import SessionService
from app.services.keycloak_service import KeycloakService
from app.middleware import AuthMiddleware

class AuthHandler:
    def __init__(self, session_service: SessionService, keycloak_service: KeycloakService):
        self.session_service = session_service
        self.keycloak_service = keycloak_service
    
    def get_auth_status(self, request: Request):
        print(f"DEBUG: Getting auth status")
        session_id = request.cookies.get("session_id")
        print(f"DEBUG: Session ID from cookie: {session_id}")
        
        if not session_id:
            print(f"DEBUG: No session ID in cookie")
            return JSONResponse(content={"isAuthenticated": False})
        
        session = self.session_service.get_session(session_id)
        print(f"DEBUG: Session from service: {session}")
        
        if not session:
            print(f"DEBUG: Session not found or invalid")
            return JSONResponse(content={"isAuthenticated": False})
        
        print(f"DEBUG: Session found, checking expiration")
        from datetime import datetime
        if datetime.now() > session.expires_at:
            print(f"DEBUG: Session expired")
            return JSONResponse(content={"isAuthenticated": False})
        
        print(f"DEBUG: Getting user info")
        user_info = self.keycloak_service.get_user_info(session.access_token)
        if not user_info:
            print(f"DEBUG: Could not get user info")
            return JSONResponse(content={"isAuthenticated": False})
        
        print(f"DEBUG: Auth status: authenticated")
        return JSONResponse(content={
            "isAuthenticated": True,
            "name": user_info.username,
            "username": user_info.username,
            "userId": user_info.user_id,
            "crm_user_id": user_info.crm_user_id
        })
    
    def login(self):
        auth_url = "http://localhost:8080/realms/reports-realm/protocol/openid-connect/auth?client_id=backend-auth&response_type=code&scope=openid bionic-pro.all&redirect_uri=http://localhost:5001/api/auth/callback"
        return RedirectResponse(url=auth_url)
    
    def logout(self, request: Request, response: Response):
        session_id = request.cookies.get("session_id")
        if not session_id:
            return RedirectResponse(url="http://localhost:3000")
        
        session = self.session_service.get_session(session_id)
        if session:
            self.keycloak_service.logout(session.refresh_token)
            self.session_service.delete_session(session_id)
        
        response.delete_cookie("session_id", path="/", domain="localhost")
        return RedirectResponse(url="http://localhost:3000")
    
    def handle_callback(self, request: Request, response: Response, code: str = None, state: str = None):
        if not code:
            return RedirectResponse(url="http://localhost:3000?error=no_code")
        
        redirect_uri = "http://localhost:5001/api/auth/callback"
        
        # Проверяем существующую сессию
        existing_session = self.session_service.get_session_by_code(code)
        if existing_session:
            response.set_cookie(
                key="session_id",
                value=existing_session.id,
                max_age=int(24 * 3600),
                path="/",
                domain="localhost",
                httponly=True,
                secure=False
            )
            return RedirectResponse(url="http://localhost:3000")
        
        # Создаем новую сессию
        session = self.session_service.create_session(code, redirect_uri)
        if not session:
            return RedirectResponse(url="http://localhost:3000?error=login_failed")
        
        response.set_cookie(
            key="session_id",
            value=session.id,
            max_age=int(24 * 3600),
            path="/",
            domain="localhost",
            httponly=True,
            secure=False
        )
        redirect = RedirectResponse(url="http://localhost:3000")
        redirect.set_cookie(
            key="session_id",
            value=session.id,
            max_age=24 * 3600,  # 24 часа
            path="/",
            domain="localhost",
            httponly=True,
            secure=False
        )
        return redirect
    
    def get_user_info(self, session):
        return JSONResponse(content={
            "id": session.user_info.id,
            "username": session.user_info.username,
            "email": session.user_info.email,
            "roles": session.user_info.roles,
            "userId": session.user_info.user_id,
            "crm_user_id": session.user_info.crm_user_id
        })
    
    def refresh_token(self, session_id: str):
        refreshed = self.session_service.refresh_session(session_id)
        if not refreshed:
            raise HTTPException(status_code=401, detail="Failed to refresh token")
        
        return JSONResponse(content={"message": "Token refreshed successfully"})
    
    def get_reports(self, session):
        if not session.user_info.crm_user_id:
            raise HTTPException(status_code=403, detail="Reports not available for this user (no CRM ID)")
        
        try:
            with httpx.Client(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {session.access_token}",
                    "X-User-ID": str(session.user_info.crm_user_id)
                }
                
                response = client.get(
                    "http://reports-api:5003/api/v1/reports",
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail="Failed to get reports")
                
                return JSONResponse(content=response.json())
                
        except Exception as e:
            print(f"Failed to get reports: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get reports")
    
    def generate_reports(self, session):
        try:
            with httpx.Client(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {session.access_token}"
                }
                
                response = client.post(
                    "http://reports-api:5003/api/v1/reports/generate",
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail="Failed to generate reports")
                
                return JSONResponse(content=response.json())
                
        except Exception as e:
            print(f"Failed to generate reports: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to generate reports")