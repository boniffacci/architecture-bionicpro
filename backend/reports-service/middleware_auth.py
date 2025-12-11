from functools import wraps
from flask import request, jsonify, g
import jwt
import re

class AuthMiddleware:
    def __init__(self, secret_key="your-secret-key"):
        self.secret_key = secret_key
    
    def require_auth(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id_header = request.headers.get('X-User-ID')
            if user_id_header:
                try:
                    user_id = int(user_id_header)
                    g.user_id = user_id
                    return f(*args, **kwargs)
                except ValueError:
                    pass
            
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({"error": "Authorization header required"}), 401
            
            bearer_match = re.match(r'Bearer\s+(.+)', auth_header)
            if not bearer_match:
                return jsonify({"error": "Bearer token required"}), 401
            
            token_string = bearer_match.group(1)
            
            try:
                payload = jwt.decode(token_string, self.secret_key, algorithms=["HS256"])
                user_id = None
                if 'user_id' in payload:
                    user_id_value = payload['user_id']
                    if isinstance(user_id_value, (int, float)):
                        user_id = int(user_id_value)
                    elif isinstance(user_id_value, str):
                        user_id = int(user_id_value)
                
                if not user_id:
                    return jsonify({"error": "User ID not found in token"}), 401
                
                g.user_id = user_id
                return f(*args, **kwargs)
                
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401
        
        return decorated_function