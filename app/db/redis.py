from redis.asyncio import Redis

from app.config import settings

"""
Create an asynchronous Redis client instance using the Redis URL from the settings.
This client will be used to interact with the Redis database for caching,
session management,or any other use cases that require fast, in-memory data storage.
The Redis client will be initialized when the application starts and can be used
throughout the application to perform Redis operations.
"""

redis_client = Redis.from_url(str(settings.redis_url))
