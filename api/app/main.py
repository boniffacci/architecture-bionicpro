import uvicorn

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError


with open("keycloak_public_key.pem", "r") as f:
    PUBLIC_KEY = f.read()

ALGORITHM = "RS256"
AUDIENCE = "reports-api"  # clientId из Keycloak


app = FastAPI(
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
)

# Настройка CORS для запросов с фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM], audience=AUDIENCE)
        roles = payload.get("realm_access", {}).get("roles", [])
        if "prothetic_user" not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для доступа"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или просроченный токен"
        )

@app.get("/reports")
async def get_reports(user: dict = Depends(verify_token)):
    # Генерация произвольных данных отчёта
    return {"status": "success", "data": "Отчёт готов"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)