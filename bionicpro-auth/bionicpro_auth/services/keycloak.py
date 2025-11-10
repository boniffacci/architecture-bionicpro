import asyncio
import base64
import hashlib
import random
import string

import jwt

from bionicpro_auth.providers.keycloak import PKCEKeycloakOpenID

from .storage import StorageService


def generate_random_string(n: int = 36) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


class KeycloackAuthError(Exception):
    pass


class KeycloakOpenIdService:
    def __init__(self):
        self.provider = PKCEKeycloakOpenID(
            server_url="http://keycloak:8080/",
            client_id="reports-frontend",
            realm_name="reports-realm",
        )

    def make_pkce_challenge(self, verifier: str) -> str:
        challenge = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")

    async def get_auth_url(self, redirect_uri: str) -> str:
        state = generate_random_string()
        pkce_verifier = generate_random_string(64)
        pkce_challenge = self.make_pkce_challenge(pkce_verifier)

        async with StorageService() as storage:
            url, *_ = await asyncio.gather(
                self.provider.a_pkce_auth_url(
                    redirect_uri=redirect_uri,
                    state=state,
                    pkce_challenge=pkce_challenge,
                ),
                storage.store_pkce_verifier(state, pkce_verifier),
            )

        return url

    async def exchange_code_for_session(
        self,
        authorization_code: str,
        state: str,
        redirect_uri: str,
    ) -> str:
        if not authorization_code:
            raise KeycloackAuthError
        if not state:
            raise KeycloackAuthError

        async with StorageService() as storage:
            pkce_verifier = (await storage.get_pkce_verifier(state)).decode()

            if not pkce_verifier:
                raise KeycloackAuthError

            tokens = await self.provider.a_token(
                grant_type="authorization_code",
                code=authorization_code,
                redirect_uri=redirect_uri,
                code_verifier=pkce_verifier,  # type: ignore
            )

            session_key = generate_random_string()
            await storage.store_tokens(
                session_key,
                tokens["access_token"],
                tokens["refresh_token"],
            )

        return session_key

    async def refresh_tokens(self, session_key: str) -> str:
        async with StorageService() as storage:
            old_tokens = await storage.get_tokens(session_key)
            if not old_tokens:
                raise KeycloackAuthError

            _, refresh_token = old_tokens
            refreshed_tokens = await self.provider.a_refresh_token(refresh_token)

            session_key = generate_random_string()
            await storage.store_tokens(
                session_key,
                refreshed_tokens["access_token"],
                refreshed_tokens["refresh_token"],
            )

        return session_key

    async def get_username(self, session_key: str) -> str:
        async with StorageService() as storage:
            tokens = await storage.get_tokens(session_key)
            if not tokens:
                raise KeycloackAuthError

            access_token, _ = tokens
            userinfo = jwt.decode(access_token, options={"verify_signature": False})[
                "preferred_username"
            ]

        return userinfo
