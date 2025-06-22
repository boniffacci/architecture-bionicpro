from fastapi import HTTPException, status
from keycloak.exceptions import KeycloakAuthenticationError
from api.config import keycloak_openid

REQUIRED_ROLES = ["prothetic_user"]

class AuthService:

    @staticmethod
    def verify_token(token: str):

        try:

            user_info = keycloak_openid.introspect(token)
            
            if not user_info.get("active"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )

            roles = user_info["realm_access"]["roles"]
            for role in REQUIRED_ROLES:
                if role not in roles:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required role: {role}",
                    )

            return user_info

        except KeycloakAuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            ) from exc