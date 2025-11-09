import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Self

import redis.asyncio as redis
from anyio import AsyncContextManagerMixin

from .encrypt import EncryptionService


class StorageService(AsyncContextManagerMixin):
    def __init__(self):
        self.redis_url = "redis://redis:6379/0"

    @asynccontextmanager
    async def __asynccontextmanager__(self) -> AsyncGenerator[Self]:
        self.storage: redis.Redis = redis.from_url(self.redis_url)
        yield self
        await self.storage.aclose()

    async def store_pkce_verifier(
        self,
        state: str,
        pkce_verifier: str,
    ) -> None:
        await self.storage.set(state, pkce_verifier)

    async def get_pkce_verifier(
        self,
        state: str,
    ) -> bytes:
        return await self.storage.get(state)

    async def clear_state(
        self,
        state: str,
    ) -> str:
        return await self.storage.delete(state)

    async def store_tokens(
        self,
        session_key: str,
        access_token: str,
        refresh_token: str,
    ) -> None:
        encryption_service = EncryptionService()
        encrypted_refresh_token = encryption_service.encrypt(refresh_token)

        await self.storage.set(
            session_key,
            json.dumps(
                {
                    "access_token": access_token,
                    "encrypted_refresh_token": encrypted_refresh_token,
                }
            ),
        )

    async def get_tokens(
        self,
        session_key: str,
    ) -> tuple[str, str] | None:
        encryption_service = EncryptionService()

        tokens_raw = await self.storage.get(session_key)
        if not tokens_raw:
            return None

        tokens = json.loads(tokens_raw)
        encrypted_refresh_token = tokens["encrypted_refresh_token"]
        refresh_token = encryption_service.decrypt(encrypted_refresh_token)

        return tokens["access_token"], refresh_token
