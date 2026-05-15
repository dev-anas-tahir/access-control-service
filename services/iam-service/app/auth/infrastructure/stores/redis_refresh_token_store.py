import uuid

from redis.asyncio import Redis


class RedisRefreshTokenStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def put(self, token: str, user_id: uuid.UUID, ttl_seconds: int) -> None:
        await self._redis.setex(f"refresh_token:{token}", ttl_seconds, str(user_id))

    async def get(self, token: str) -> uuid.UUID | None:
        value = await self._redis.get(f"refresh_token:{token}")
        if not value:
            return None
        return uuid.UUID(value.decode())

    async def delete(self, token: str) -> None:
        await self._redis.delete(f"refresh_token:{token}")
