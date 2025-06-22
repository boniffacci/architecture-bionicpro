import random
import string
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.models import Report
from api.service import AuthService

# Initialize HTTPBearer security dependency
bearer_scheme = HTTPBearer()

class AuthController:

    @staticmethod
    def protected_endpoint(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    ) ->Report:
        """
        Access a protected resource that requires valid token authentication.

        Args:
            credentials (HTTPAuthorizationCredentials): Bearer token provided
            via HTTP Authorization header.

        Raises:
            HTTPException: If the token is invalid or not provided.

        Returns:
            UserInfo: Information about the authenticated user.
        """
        # Extract the bearer token from the provided credentials
        token = credentials.credentials

        # Verify the token and get user information
        user_info = AuthService.verify_token(token)

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
                        
        report_data = {
                "report_id": random.randint(1000, 9999),
                "title": f"Report {random.choice(string.ascii_uppercase)}",
                "data": [random.randint(1, 100) for _ in range(10)],
                "summary": "This is a summary of the report data."
            }
        


        return Report(**report_data)