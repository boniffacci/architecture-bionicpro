import httpx
import json
from typing import Optional, Dict, Any
from app.config import config
from app.models.session import TokenResponse, UserInfo

class KeycloakService:
    def __init__(self):
        self.config = {
            "url": config.keycloak_url,
            "client_id": config.keycloak_client_id,
            "secret": config.keycloak_secret,
            "realm": config.keycloak_realm
        }
        self.client = httpx.Client(timeout=30.0)
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[TokenResponse]:
        token_url = f"{self.config['url']}/realms/{self.config['realm']}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "authorization_code",
            "client_id": self.config['client_id'],
            "client_secret": self.config['secret'],
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        try:
            response = self.client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                return TokenResponse(**token_data)
            else:
                print(f"Token exchange failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Token exchange error: {str(e)}")
            return None
    
    def refresh_token(self, refresh_token: str) -> Optional[TokenResponse]:
        token_url = f"{self.config['url']}/realms/{self.config['realm']}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.config['client_id'],
            "client_secret": self.config['secret'],
            "refresh_token": refresh_token
        }
        
        try:
            response = self.client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                return TokenResponse(**token_data)
            else:
                print(f"Token refresh failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Token refresh error: {str(e)}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[UserInfo]:
        userinfo_url = f"{self.config['url']}/realms/{self.config['realm']}/protocol/openid-connect/userinfo"
        
        try:
            response = self.client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"userInfo {user_data}")
                
                info = UserInfo(
                    id=self._get_string(user_data, "sub"),
                    username=self._get_string(user_data, "preferred_username"),
                    email=self._get_string(user_data, "email"),
                    roles=[]
                )
                
                # Parse user_id
                user_id_str = self._get_string(user_data, "user_id")
                if user_id_str:
                    try:
                        info.user_id = int(user_id_str)
                    except ValueError:
                        info.user_id = 0
                
                # Parse crm_user_id
                crm_user_id_str = self._get_string(user_data, "crm_user_id")
                if crm_user_id_str:
                    try:
                        info.crm_user_id = int(crm_user_id_str)
                    except ValueError:
                        info.crm_user_id = None
                
                # Parse roles
                if "roles" in user_data and isinstance(user_data["roles"], list):
                    for role in user_data["roles"]:
                        if isinstance(role, str):
                            info.roles.append(role)
                
                return info
            else:
                print(f"User info failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"User info error: {str(e)}")
            return None
    
    def logout(self, refresh_token: str) -> bool:
        logout_url = f"{self.config['url']}/realms/{self.config['realm']}/protocol/openid-connect/logout"
        
        data = {
            "client_id": self.config['client_id'],
            "client_secret": self.config['secret'],
            "refresh_token": refresh_token
        }
        
        try:
            response = self.client.post(
                logout_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            return response.status_code in [200, 204]
                
        except Exception as e:
            print(f"Logout error: {str(e)}")
            return False
    
    def _get_string(self, data: Dict[str, Any], key: str) -> str:
        if key in data and isinstance(data[key], str):
            return data[key]
        return ""