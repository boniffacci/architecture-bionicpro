# from dotenv import load_dotenv
import csv
import io
import os

from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from keycloak import KeycloakOpenID

# load_dotenv()

KEYCLOAK_URL = os.environ.get("API_APP_KEYCLOAK_URL")
KEYCLOAK_REALM = os.environ.get("API_APP_KEYCLOAK_REALM")
KEYCLOAK_CLIENT_ID = os.environ.get("API_APP_KEYCLOAK_CLIENT_ID")

if not all([KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID]):
  raise EnvironmentError("Не все обязательные переменные окружения установлены")

keycloak_openid = KeycloakOpenID(
  server_url=KEYCLOAK_URL,
  realm_name=KEYCLOAK_REALM,
  client_id=KEYCLOAK_CLIENT_ID
)

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"]
)

token_scheme = HTTPBearer()

async def verify_bearer_token(
  token: HTTPAuthorizationCredentials = Security(token_scheme),
):
  try:
    payload = keycloak_openid.decode_token(token.credentials)
  except Exception as e:
    raise HTTPException(status_code=401, detail=f"Невалидный токен: {str(e)}")

  all_user_roles = payload.get("realm_access", {}).get("roles", [])

  if 'prothetic_user' not in all_user_roles:
    raise HTTPException(status_code=403, detail="Недостаточно прав")

stub_report_data = [
  ["Name", "Age", "City"],
  ["Alice", 30, "New York"],
  ["Bob", 25, "Los Angeles"],
  ["Charlie", 35, "Chicago"]
]

@app.get("/reports")
def get_reports(_=Depends(verify_bearer_token)):
  stream = io.StringIO()
  writer = csv.writer(stream)
  writer.writerows(stub_report_data)

  response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
  response.headers["Content-Disposition"] = "attachment; filename=report.csv"

  return response