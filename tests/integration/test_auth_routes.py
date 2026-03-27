from httpx import AsyncClient, Response


async def test_signup_success(client: AsyncClient, viewer_role):
    # 1. Set the payload
    payload = {
        "username": "newuser456",
        "email": "new456@example.com",
        "password": "SecurePass2025!",
    }

    # 2. Call the api endpoint with payload
    response: Response = await client.post("/api/v1/auth/signup", json=payload)

    # 3. Assert the response tp be 201
    assert response.status_code == 201

    # 3. Grab the data from the response object
    data = response.json()

    # 4. Look all the required/expected keys are present in the data
    expected_keys = {
        "id",
        "username",
        "email",
        "created_at",
    }
    assert set(data.keys()) >= expected_keys, (
        f"Missing keys: {expected_keys - set(data.keys())}"
    )

    # 5. Assert wether the fields value are correct or not
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]

    # 6. Sensitive keys are not present in the response
    forbidden_keys = {"password", "password_hash", "hashed_password"}
    for key in forbidden_keys:
        assert key not in data, f"Sensitive field '{key}' leaked in response"


async def test_signup_duplicate_username(client, viewer_role):
    # 1. Set the payload
    payload = {
        "username": "newuser456",
        "email": "new456@example.com",
        "password": "SecurePass2025!",
    }

    # 2. Call the api endpoint with payload (twice)
    await client.post("/api/v1/auth/signup", json=payload)
    response: Response = await client.post("/api/v1/auth/signup", json=payload)

    # 3. Assert the response tp be 409
    assert response.status_code == 409


async def test_login_success(client, viewer_role):
    # 1. Set the payload for signup
    payload = {
        "username": "newuser456",
        "password": "SecurePass2025!",
    }

    # 2. Call the signup api endpoint
    await client.post("/api/v1/auth/signup", json=payload)

    # 3. Call the login api endpoint (uses real JWT encoding with test keys)
    response: Response = await client.post("/api/v1/auth/login", json=payload)

    # 4. Assert the status code 200
    assert response.status_code == 200

    # 5. Grab the data from the response object
    data = response.json()

    # 6. Look access_token is present in the data
    expected_keys = {
        "access_token",
    }
    assert set(data.keys()) >= expected_keys, (
        f"Missing keys: {expected_keys - set(data.keys())}"
    )

    # 7. Sensitive keys are not present in the response
    forbidden_keys = {"password", "password_hash", "hashed_password"}
    for key in forbidden_keys:
        assert key not in data, f"Sensitive field '{key}' leaked in response"

    # 8. Assert refresh_token cookie is set
    assert response.cookies.get("refresh_token") is not None


async def test_login_wrong_password(client, viewer_role):
    # 1. Signup
    await client.post(
        "/api/v1/auth/signup",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        },
    )

    # 2. Login with wrong password — no JWT mock needed, fails before token creation
    response: Response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "WrongPassword123!"},
    )

    assert response.status_code == 401
