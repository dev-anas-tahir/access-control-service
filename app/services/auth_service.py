"""
This module defines the AuthService, which contains business logic
related to authentication and user management, such as signing up
new users. The AuthService interacts with the database to perform
operations like creating users and assigning roles.

Example:
    ```python
    from app.services.auth_service import signup

    # Create a new user
    new_user = await signup(db_session, signup_data)
    ```
"""

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import NotFoundError, UniquenessError
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.db.redis import redis_client
from app.models.association import UserRole
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest


async def signup(db: AsyncSession, data: SignupRequest) -> User:
    """
    Sign up a new user by creating a User record in the database.

    This function validates the uniqueness of the username and email, hashes the
    password, and assigns the default 'viewer' role to the new user.

    Args:
        db: The database session used to perform operations.
        data: The data required to create a new user, including username,
            email, and password.

    Returns:
        The newly created User object with assigned role.

    Raises:
        UniquenessError: If the username or email already exists in the database.
        RuntimeError: If the default 'viewer' role is not found in the database.

    Example:
        ```python
        from app.schemas.auth import SignupRequest

        signup_data = SignupRequest(
            username="john_doe",
            password="SecurePass123!",
            email="john@example.com"
        )
        new_user = await signup(db_session, signup_data)
        ```
    """
    # 1. Check username uniqueness
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise UniquenessError("Username already exists")

    # 2. Check email uniqueness
    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise UniquenessError("Email already exists")

    # 3. Hash the password
    password_hash = hash_password(data.password)

    # 4. Create the user
    new_user = User(
        username=data.username,
        email=data.email,
        password_hash=password_hash,
    )
    db.add(new_user)
    await db.flush()  # generates new_user.id without committing

    # 5. Fetch default viewer role
    result = await db.execute(select(Role).where(Role.name == "viewer"))
    viewer_role = result.scalar_one_or_none()
    if not viewer_role:
        raise RuntimeError("Default 'viewer' role not found. Run seed script first.")

    # 6. Assign viewer role
    user_role = UserRole(user_id=new_user.id, role_id=viewer_role.id)
    db.add(user_role)

    # 7. Commit and refresh
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def login(db: AsyncSession, data: LoginRequest) -> str:
    """
    Authenticate a user by verifying their username and password.

    If authentication is successful, a new access token and refresh token are
    generated and returned.

    Args:
        db: The database session used to perform operations.
        data: The data required for login, including username and password.

    Returns:
        Tuple[str, str]: A tuple containing the new access token and refresh token
            if authentication is successful.

    Raises:
        ValueError: If the username does not exist or the password is incorrect.

    Example:
        ```python
        from app.schemas.auth import LoginRequest

        login_data = LoginRequest(
            username="john_doe",
            password="SecurePass123!"
        )
        access_token, refresh_token = await login(db_session, login_data)
        ```
    """
    # 1. check if the username exists in the db
    result = await db.execute(
        select(User)
        .where(User.username == data.username)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise ValueError("Invalid username or password")

    # 2. Hash the given password and compare it with the stored password hash
    if not verify_password(data.password, user.password_hash):
        raise ValueError("Invalid username or password")

    # 3. If the password is correct, look to update the has algorithm
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
        db.add(user)
        await db.commit()

    # 4. Generate a new access token and return it to the user
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        roles=[role.name for role in user.roles],
        permissions=[
            perm.scope_key for role in user.roles for perm in role.permissions
        ],
        is_super_user=user.is_super_user,
    )

    # 5. Generate refresh token and store it into the redis
    refresh_token = secrets.token_urlsafe(64)
    ttl_seconds = settings.jwt_refresh_token_expire_days * 24 * 3600
    await redis_client.setex(
        f"refresh_token:{refresh_token}",
        ttl_seconds,
        str(user.id),
    )

    return access_token, refresh_token


async def refresh_token(db: AsyncSession, refresh_token: str) -> str:
    """
    Refresh an access token using a valid refresh token.

    This function checks the validity of the refresh token, retrieves the
    associated user, and generates a new access token. It also rotates the
    refresh token by generating a new one.

    Args:
        db: The database session used to perform operations.
        refresh_token: The refresh token provided by the client.

    Returns:
        Tuple[str, str]: A tuple containing the new access token and the new
            refresh token if the refresh token is valid.

    Raises:
        ValueError: If the refresh token is invalid or expired.
        NotFoundError: If the user not exists or is inactive

    Example:
        ```python
        access_token, new_refresh_token = await refresh_token(db_session, old_refresh_token)
        ```
    """  # noqa: E501
    # 1. Check if the refresh token exists in Redis
    user_id = await redis_client.get(f"refresh_token:{refresh_token}")
    if not user_id:
        raise ValueError("Invalid or expired refresh token")

    # 2. Retrieve the user from the database
    result = await db.execute(
        select(User)
        .where(User.id == uuid.UUID(user_id.decode()))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise NotFoundError("User not found or inactive")

    # 3. Generate a new access token
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        roles=[role.name for role in user.roles],
        permissions=[
            perm.scope_key for role in user.roles for perm in role.permissions
        ],
        is_super_user=user.is_super_user,
    )

    # 4. Rotate the refresh token by generating a new one and updating it in Redis
    await redis_client.delete(f"refresh_token:{refresh_token}")

    new_refresh_token = secrets.token_urlsafe(64)
    ttl_seconds = settings.jwt_refresh_token_expire_days * 24 * 3600
    await redis_client.setex(
        f"refresh_token:{new_refresh_token}", ttl_seconds, str(user.id)
    )

    return access_token, new_refresh_token


async def logout(refresh_token: str, payload: dict) -> None:
    """
    Log out a user by invalidating their refresh token.

    This function invalidates the refresh token by deleting it from Redis,
    ensuring it can no longer be used to generate new access tokens. It also
    revokes the access token by adding its JTI to a revoked tokens list.

    Args:
        refresh_token: The refresh token to be invalidated.
        payload: The decoded JWT payload containing token information.

    Example:
        ```python
        await logout(refresh_token, jwt_payload)
        ```
    """
    # 1. Delete the refresh token from Redis to invalidate it
    await redis_client.delete(f"refresh_token:{refresh_token}")

    # 2. Revoke access token JTI
    jti = payload["jti"]
    exp = payload["exp"]
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = max(exp - now, 0)  # remaining lifetime in seconds
    if ttl > 0:
        await redis_client.setex(f"revoked_jti:{jti}", ttl, "1")
