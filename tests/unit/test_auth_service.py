from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import UniquenessError
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest
from app.services import auth_service


@pytest.mark.asyncio
async def test_signup_success(db, viewer_role):
    # 1. Create signup data
    signup_data = SignupRequest(
        username="testuser", password="TestPassword123!", email="test@example.com"
    )

    # 2. Call signup function
    user = await auth_service.signup(db, signup_data)

    # 3. Assert user was created successfully
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.password_hash is not None
    assert user.id is not None
    assert user.password_hash != "TestPassword123!"  # must be hashed

    # 4. Reload with roles explicitly — async doesn't support lazy loading
    result = await db.execute(
        select(User).where(User.id == user.id).options(selectinload(User.roles))
    )
    user_with_roles = result.scalar_one()
    assert len(user_with_roles.roles) == 1
    assert user_with_roles.roles[0].name == "viewer"


@pytest.mark.asyncio
async def test_signup_duplicate_username(db, viewer_role):
    # 1. First, create a user
    signup_data = SignupRequest(
        username="testuser", password="TestPassword123!", email="test@example.com"
    )
    await auth_service.signup(db, signup_data)

    # 2. Try to create another user with the same username
    duplicate_signup_data = SignupRequest(
        username="testuser",  # Same username
        password="AnotherPassword123!",
        email="another@example.com",
    )

    # 3. Should raise UniquenessError
    with pytest.raises(UniquenessError, match="Username already exists"):
        await auth_service.signup(db, duplicate_signup_data)


@pytest.mark.asyncio
async def test_signup_duplicate_email(db, viewer_role):

    # First, create a user
    signup_data = SignupRequest(
        username="testuser", password="TestPassword123!", email="test@example.com"
    )
    await auth_service.signup(db, signup_data)

    # Try to create another user with the same email
    duplicate_signup_data = SignupRequest(
        username="differentuser",  # Different username
        password="AnotherPassword123!",
        email="test@example.com",  # Same email
    )

    # Should raise UniquenessError
    with pytest.raises(UniquenessError, match="Email already exists"):
        await auth_service.signup(db, duplicate_signup_data)


@pytest.mark.asyncio
async def test_login_success(db, viewer_role):
    # 1. First, create a user
    signup_data = SignupRequest(
        username="testuser", password="TestPassword123!", email="test@example.com"
    )
    await auth_service.signup(db, signup_data)

    # 2. Mock Redis client and JWT functionality to avoid needing actual keys
    with (
        patch("app.services.auth_service.redis_client") as mock_redis,
        patch("app.core.security.key_pair") as mock_key_pair,
    ):
        mock_redis.setex = AsyncMock()
        # Mock the key pair to return dummy keys
        mock_key_pair.private_key = "dummy_private_key"
        mock_key_pair.public_key = "dummy_public_key"

        # Mock jwt.encode to return a dummy token
        with patch("jwt.encode", return_value="dummy_access_token"):
            # 3. Create login data
            login_data = LoginRequest(username="testuser", password="TestPassword123!")

            # 4. Call login function
            access_token, refresh_token = await auth_service.login(db, login_data)

            # 5. Assert both tokens are returned
            assert isinstance(access_token, str)
            assert isinstance(refresh_token, str)

            # 6. Verify access token is a string
            assert access_token == "dummy_access_token"

            # 7. Verify refresh token is a URL-safe string of appropriate length
            assert (
                len(refresh_token) >= 64
            )  # secrets.token_urlsafe(64) generates at least 64 chars

            # 8. Verify Redis was called to store the refresh token
            mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_login_wrong_password(db, viewer_role):
    # 1. First, create a user
    signup_data = SignupRequest(
        username="testuser", password="TestPassword123!", email="test@example.com"
    )
    await auth_service.signup(db, signup_data)

    # 2. Mock JWT functionality to avoid needing actual keys
    with patch("app.core.security.key_pair") as mock_key_pair:
        mock_key_pair.private_key = "dummy_private_key"
        mock_key_pair.public_key = "dummy_public_key"

        # Mock jwt.encode to return a dummy token
        with patch("jwt.encode", return_value="dummy_access_token"):
            # 3. Create login data with wrong password
            login_data = LoginRequest(username="testuser", password="WrongPassword123!")

            # 4. Should raise ValueError
            with pytest.raises(ValueError, match="Invalid username or password"):
                await auth_service.login(db, login_data)


@pytest.mark.asyncio
async def test_login_inactive_user(db, viewer_role):
    # 1. First, create a user
    signup_data = SignupRequest(
        username="testuser", password="TestPassword123!", email="test@example.com"
    )
    user = await auth_service.signup(db, signup_data)

    # 2. Make the user inactive
    user.is_active = False
    db.add(user)
    await db.flush()

    # 3. Mock JWT functionality to avoid needing actual keys
    with patch("app.core.security.key_pair") as mock_key_pair:
        mock_key_pair.private_key = "dummy_private_key"
        mock_key_pair.public_key = "dummy_public_key"

        # Mock jwt.encode to return a dummy token
        with patch("jwt.encode", return_value="dummy_access_token"):
            # 4. Create login data
            login_data = LoginRequest(username="testuser", password="TestPassword123!")

            # 5. Should raise ValueError
            with pytest.raises(ValueError, match="Invalid username or password"):
                await auth_service.login(db, login_data)


@pytest.mark.asyncio
async def test_login_nonexistent_username(db):
    # 1. Mock JWT functionality to avoid needing actual keys
    with patch("app.core.security.key_pair") as mock_key_pair:
        mock_key_pair.private_key = "dummy_private_key"
        mock_key_pair.public_key = "dummy_public_key"

        # Mock jwt.encode to return a dummy token
        with patch("jwt.encode", return_value="dummy_access_token"):
            # 2. Create login data with non-existent username
            login_data = LoginRequest(
                username="nonexistent", password="AnyPassword123!"
            )

            # 3. Should raise ValueError
            with pytest.raises(ValueError, match="Invalid username or password"):
                await auth_service.login(db, login_data)
