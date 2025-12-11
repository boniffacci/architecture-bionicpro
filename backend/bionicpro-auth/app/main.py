from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from app.config import config
from app.services.session_service import SessionService
from app.services.keycloak_service import KeycloakService
from app.middleware import AuthMiddleware
from app.handlers.auth_handler import AuthHandler

# Инициализация сервисов
redis_service = None  # Будет инициализирован в SessionService
keycloak_service = KeycloakService()
session_service = SessionService()
auth_middleware = AuthMiddleware(session_service)
auth_handler = AuthHandler(session_service, keycloak_service)

app = FastAPI()

# CORS middleware
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Origin, Content-Type, Accept, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.middleware("http")
async def options_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse(content={}, headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Origin, Content-Type, Accept, Authorization",
            "Access-Control-Allow-Credentials": "true"
        })
    return await call_next(request)

# Эндпоинты
@app.get("/health")
async def health():
    return JSONResponse(content={"status": "ok"})

@app.get("/login")
async def login():
    return auth_handler.login()

@app.get("/auth/logout")
async def logout(request: Request, response: Response):
    return auth_handler.logout(request, response)

# API группа
from fastapi import APIRouter, Depends

api_router = APIRouter(prefix="/api")

@api_router.get("/auth/status")
async def auth_status(request: Request):
    return auth_handler.get_auth_status(request)

@api_router.get("/auth/login")
async def api_login():
    return auth_handler.login()

@api_router.get("/auth/logout")
async def api_logout(request: Request, response: Response):
    return auth_handler.logout(request, response)

@api_router.get("/auth/callback")
async def auth_callback(request: Request, response: Response, code: str = None, state: str = None):
    return auth_handler.handle_callback(request, response, code, state)

@api_router.get("/auth/me")
async def get_me(request: Request):
    # Проверяем аутентификацию через middleware
    middleware_result = await auth_middleware.require_auth()(request)
    if middleware_result:
        return middleware_result
    return auth_handler.get_user_info(request.state.session)

@api_router.post("/auth/refresh")
async def refresh(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session found")
    return auth_handler.refresh_token(session_id)

@api_router.get("/reports")
async def get_reports(request: Request):
    middleware_result = await auth_middleware.require_auth()(request)
    if middleware_result:
        return middleware_result
    return auth_handler.get_reports(request.state.session)

@api_router.post("/reports/generate")
async def generate_reports(request: Request):
    middleware_result = await auth_middleware.require_auth()(request)
    if middleware_result:
        return middleware_result
    return auth_handler.generate_reports(request.state.session)

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    print(f"Starting bionicpro-auth server on :{config.app_port}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.app_port,
        reload=config.app_debug
    )