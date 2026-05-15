from redis.asyncio import Redis


class RedisRevocationStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        await self._redis.setex(f"revoked_jti:{jti}", ttl_seconds, "1")

    async def is_revoked(self, jti: str) -> bool:
        return bool(await self._redis.get(f"revoked_jti:{jti}"))
