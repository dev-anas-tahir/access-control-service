import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import UniquenessError
from app.models.user import User
from app.schemas.auth import SignupRequest
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
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.roles))
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
