# app/core/rate_limit.py
from fastapi import Depends, HTTPException, Request, status

from app.db.redis import redis_client

# Config
IP_MAX_ATTEMPTS = 20  # per 60 seconds
IP_WINDOW = 60  # seconds

USERNAME_MAX_ATTEMPTS = 5  # per 300 seconds
USERNAME_WINDOW = 300  # seconds


async def rate_limit_by_ip(request: Request) -> None:
    # 1. Extract IP from request if not retuen
    ip_address = request.client.host if request.client else "unknown"
    if not ip_address:
        return

    # 2. build Redis key
    endpoint = request.url.path
    redis_key = f"rate_limit:ip:{ip_address}:{endpoint}"

    # 3. INCR the counter
    count = await redis_client.incr(redis_key)

    # 4. if count == 1: set TTL (first request in window)
    if count == 1:
        await redis_client.expire(redis_key, IP_WINDOW)

    # 5. if count > limit: raise 429
    if count > IP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded (IP). Try again later.",
            headers={"Retry-After": str(IP_WINDOW)},
        )


async def rate_limit_by_username(request: Request) -> None:
    # 1. Parse username from request body
    try:
        body = await request.json()
    except Exception:
        return
    username = body.get("username")
    if not username or not isinstance(username, str):
        return
    username = username.lower().strip()

    # 2. Build Redis key
    endpoint = request.url.path
    redis_key = f"rate_limit:username:{username}:{endpoint}"

    # 3. Same INCR pattern
    count = await redis_client.incr(redis_key)

    # 4. If count == 1: set TTL (first request in window)
    if count == 1:
        await redis_client.expire(redis_key, USERNAME_WINDOW)

    # 5. raise 429 if exceeded
    if count > USERNAME_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded (USERNAME). Try again later.",
            headers={"Retry-After": str(USERNAME_WINDOW)},
        )
