from uuid import uuid4
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="BionicPro"
)

@app.get("/reports")
def reports():
    return JSONResponse([
        dict(
            id=str(uuid4()),
            text=f"Data {ind}",
        ) 
        for ind in range(10)
    ])


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
