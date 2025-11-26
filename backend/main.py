from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from clickhouse_driver import Client
import jwt
from jwt import PyJWKClient
import pandas as pd
import json


app = FastAPI(title="My API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  
)

@app.get("/reports")
async def get_reports(authorization: str = Header()):
        
    print(authorization)
    
    jwt_payload = verify_jwt(authorization)
    print(jwt_payload)
            
    try:    

        client = Client(host='olap_db', user='default', port=9000)
         
        result , columns = client.execute(f"SELECT * FROM usage_reports WHERE user_id = '{jwt_payload['sub']}'",with_column_types=True)
        df=pd.DataFrame(result,columns=[tuple[0] for tuple in columns])        
        reports = json.loads(df.to_json(orient='records', date_format='iso'))
        return reports
                
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"message": e.detail}
        )
    except Exception as e:
        print(f"Произошла ошибка: {e}")


@app.options("/reports")
async def options_reports():
    return {"message": "OK"}

def verify_jwt(token: str):
    # Удаляем "Bearer " если есть
    if token.startswith("Bearer "):
        token = token[7:]
    
    print(token)
    try:
        
        jwks_url = f"http://keycloak:8080/realms/reports-realm/protocol/openid-connect/certs"
        
        jwks_client = PyJWKClient(jwks_url)
        
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Декодируем и верифицируем токен
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True
            }
        )
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен истек"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен"
        )
        