from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
import httpx
import logging
import json
import re
import base64
import hashlib
from urllib.parse import unquote_plus, urlencode

app = FastAPI(title="Yandex OAuth Proxy")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("yandex-proxy")

pkce_cache: dict[str, str] = {}

YANDEX_AUTH = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN = "https://oauth.yandex.ru/token"
YANDEX_INFO = "https://login.yandex.ru/info"

@app.get("/health")
async def health_check():
    return {"ok": True}

@app.get("/authorize")
async def start_auth(request: Request):
    params = dict(request.query_params)
    log.info(f"Authorize input: {params}")

    if "scope" in params:
        original = params["scope"]
        updated = re.sub(r"\bopenid\b\s*", "", original).strip()
        updated = re.sub(r"\s+", " ", updated)
        params["scope"] = updated
        log.info(f"Scopes changed: {original} -> {updated}")

    try:
        cc = params.get("code_challenge")
        nonce = params.get("nonce")
        if cc and nonce:
            pkce_cache[cc] = nonce
            log.info(f"Cached nonce for challenge {cc[:10]}")
    except Exception as e:
        log.warning(f"PKCE mapping error: {e}")

    redirect_url = f"{YANDEX_AUTH}?{urlencode(params)}"
    log.info(f"Redirect → {redirect_url}")
    return RedirectResponse(redirect_url)

@app.post("/token")
async def token_exchange(request: Request):
    raw = await request.body()
    incoming: dict[str, str] = {}

    if raw:
        for item in raw.decode().split("&"):
            if "=" in item:
                k, v = item.split("=", 1)
                incoming[unquote_plus(k)] = unquote_plus(v)

    log.info(f"Token input: {incoming}")

    async with httpx.AsyncClient() as client:
        y_resp = await client.post(
            YANDEX_TOKEN,
            data=incoming,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        log.info(f"Yandex token response {y_resp.status_code}: {y_resp.text}")

        if y_resp.status_code != 200:
            return Response(y_resp.content, status_code=y_resp.status_code, headers=dict(y_resp.headers))

        tokens = y_resp.json()

        if "id_token" not in tokens:
            try:
                userinfo_resp = await client.get(
                    YANDEX_INFO,
                    headers={"Authorization": f"OAuth {tokens.get('access_token')}"}
                )
                info = userinfo_resp.json() if userinfo_resp.status_code == 200 else {}
                user_id = info.get("id", "yandex_user")
            except Exception:
                user_id = "yandex_user"

            header = {"alg": "none", "typ": "JWT"}
            payload = {
                "iss": "https://oauth.yandex.ru",
                "sub": user_id,
                "aud": tokens.get("client_id", "8f4e26e9fc2e49bb95ead41d83bbfc03"),
                "exp": 9999999999,
                "iat": 1726517000
            }

            try:
                verifier = incoming.get("code_verifier")
                if verifier:
                    digest = hashlib.sha256(verifier.encode()).digest()
                    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
                    nonce = pkce_cache.get(challenge)
                    if nonce:
                        payload["nonce"] = nonce
                        log.info("Nonce restored")
            except Exception as e:
                log.warning(f"Nonce attach failed: {e}")

            h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
            p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
            tokens["id_token"] = f"{h_b64}.{p_b64}."

            log.info("Fake id_token generated")

        return Response(
            content=json.dumps(tokens),
            status_code=y_resp.status_code,
            headers={"Content-Type": "application/json", "Cache-Control": "no-store"}
        )

@app.get("/info")
async def info_proxy(request: Request):
    hdrs = dict(request.headers)
    hdrs.pop("host", None)

    async with httpx.AsyncClient() as client:
        y = await client.get(YANDEX_INFO, headers=hdrs)

        if y.status_code != 200:
            return Response(y.content, y.status_code, headers=dict(y.headers))

        data = y.json()

        if "id" in data and "sub" not in data:
            data["sub"] = data["id"]

        if "default_email" in data and "email" not in data:
            data["email"] = data["default_email"]

        return Response(
            json.dumps(data),
            status_code=200,
            headers={"Content-Type": "application/json", "Cache-Control": "no-store"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)