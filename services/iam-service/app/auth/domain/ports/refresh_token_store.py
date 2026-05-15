import uuid
from typing import Protocol


class RefreshTokenStore(Protocol):
    async def put(self, token: str, user_id: uuid.UUID, ttl_seconds: int) -> None: ...

    async def get(self, token: str) -> uuid.UUID | None: ...

    async def delete(self, token: str) -> None: ...
