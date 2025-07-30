from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

from auth import verify_token, get_current_user, require_prothetic_user
from reports import generate_mock_report, get_report_summary, UsageReport

# Create FastAPI app
app = FastAPI(
    title="BionicPRO Reports API",
    version="1.0.0",
    description="API для работы с отчетами по использованию бионических протезов"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "BionicPRO Reports API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/reports", response_model=UsageReport)
async def get_full_report(current_user: dict = Depends(require_prothetic_user)):
    """
    Получить полный отчет об использовании протеза.
    Доступно только пользователям с ролью 'prothetic_user'.
    """
    try:
        report = generate_mock_report(current_user)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@app.get("/reports/summary")
async def get_report_summary_endpoint(current_user: dict = Depends(require_prothetic_user)):
    """
    Получить краткую сводку отчета.
    Доступно только пользователям с ролью 'prothetic_user'.
    """
    try:
        summary = get_report_summary(current_user)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@app.get("/user/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Получить профиль текущего пользователя"""
    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "roles": current_user["roles"],
        "has_report_access": "prothetic_user" in current_user["roles"]
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )

if __name__ == "__main__":
    # For development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )