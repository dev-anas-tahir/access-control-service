from typing import Protocol


class RevocationStore(Protocol):
    async def revoke(self, jti: str, ttl_seconds: int) -> None: ...

    async def is_revoked(self, jti: str) -> bool: ...
