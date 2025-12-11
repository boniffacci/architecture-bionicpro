import json
import redis
from datetime import timedelta
from typing import Optional
from app.config import config
from app.models.session import Session

class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password,
            db=config.redis_db,
            decode_responses=False
        )
    
    def set_session(self, session: Session) -> bool:
        try:
            # Convert to dict and ensure all fields are serializable
            session_dict = session.dict()
            
            # Convert datetime objects to ISO format strings
            from datetime import datetime
            if isinstance(session_dict['expires_at'], datetime):
                session_dict['expires_at'] = session_dict['expires_at'].isoformat()
            if isinstance(session_dict['created_at'], datetime):
                session_dict['created_at'] = session_dict['created_at'].isoformat()
            
            print(f"DEBUG: Setting session dict: {session_dict.keys()}")
            print(f"DEBUG: user_info type: {type(session_dict['user_info'])}")
            
            # Ensure user_info is properly serialized
            if 'user_info' in session_dict:
                user_info = session_dict['user_info']
                if hasattr(user_info, 'dict'):
                    session_dict['user_info'] = user_info.dict()
                print(f"DEBUG: user_info keys after conversion: {session_dict['user_info'].keys()}")
            
            data = json.dumps(session_dict).encode('utf-8')
            
            pipe = self.client.pipeline()
            pipe.setex(
                f"session:{session.id}",
                timedelta(hours=24),
                data
            )
            
            if session.auth_code:
                pipe.setex(
                    f"code:{session.auth_code}",
                    timedelta(hours=24),
                    session.id.encode('utf-8')
                )
            
            pipe.execute()
            print(f"DEBUG: Session saved to Redis: {session.id}")
            return True
        except Exception as e:
            print(f"Error setting session: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def get_session(self, session_id: str) -> Optional[Session]:
        try:
            print(f"DEBUG: Getting session from Redis: session:{session_id}")
            data = self.client.get(f"session:{session_id}")
            
            if not data:
                print(f"DEBUG: No session data found for {session_id}")
                return None
            
            print(f"DEBUG: Raw session data from Redis: {data[:200]}...")
            session_dict = json.loads(data.decode('utf-8'))
            print(f"DEBUG: Parsed session dict keys: {session_dict.keys()}")
            
            # Convert string dates back to datetime
            from datetime import datetime
            if 'expires_at' in session_dict:
                try:
                    # Handle different date formats
                    expires_str = session_dict['expires_at']
                    if 'T' in expires_str:
                        session_dict['expires_at'] = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                    else:
                        session_dict['expires_at'] = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S.%f")
                    print(f"DEBUG: Parsed expires_at: {session_dict['expires_at']}")
                except Exception as e:
                    print(f"DEBUG: Error parsing expires_at: {e}")
                    return None
            
            if 'created_at' in session_dict:
                try:
                    created_str = session_dict['created_at']
                    if 'T' in created_str:
                        session_dict['created_at'] = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    else:
                        session_dict['created_at'] = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S.%f")
                    print(f"DEBUG: Parsed created_at: {session_dict['created_at']}")
                except Exception as e:
                    print(f"DEBUG: Error parsing created_at: {e}")
                    return None
            
            # Print user_info for debugging
            if 'user_info' in session_dict:
                print(f"DEBUG: user_info keys: {session_dict['user_info'].keys()}")
            
            session = Session(**session_dict)
            print(f"DEBUG: Session created successfully: {session.id}")
            return session
            
        except Exception as e:
            print(f"Error getting session: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_session_by_code(self, code: str) -> Optional[Session]:
        try:
            session_id = self.client.get(f"code:{code}")
            if not session_id:
                return None
            
            return self.get_session(session_id.decode('utf-8'))
        except Exception as e:
            print(f"Error getting session by code: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        try:
            # Get session to delete code mapping
            session = self.get_session(session_id)
            if session and session.auth_code:
                self.client.delete(f"code:{session.auth_code}")
            
            deleted = self.client.delete(f"session:{session_id}")
            return deleted > 0
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def set_access_token(self, user_id: str, token: str, expiration: int) -> bool:
        try:
            return bool(self.client.setex(
                f"access_token:{user_id}",
                expiration,
                token.encode('utf-8')
            ))
        except Exception as e:
            print(f"Error setting access token: {e}")
            return False
    
    def get_access_token(self, user_id: str) -> Optional[str]:
        try:
            token = self.client.get(f"access_token:{user_id}")
            return token.decode('utf-8') if token else None
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None
    
    def delete_access_token(self, user_id: str) -> bool:
        try:
            deleted = self.client.delete(f"access_token:{user_id}")
            return deleted > 0
        except Exception as e:
            print(f"Error deleting access token: {e}")
            return False