from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 
from handlers.auth import router as auth_router

app = FastAPI(title="BionicPro Auth")

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/auth")

@app.get("/health")
async def health():
    return {"status": "healthy"}