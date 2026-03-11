"""
Service layer for the access control service.

This package contains business logic services that handle authentication
and authorization operations, including user management, token handling,
and access control enforcement.

Services are designed to:
- Encapsulate business logic
- Handle database operations
- Manage authentication flows
- Provide secure access control mechanisms

Example:
    ```python
    from app.services.auth_service import signup, login

    # Sign up a new user
    new_user = await signup(db_session, signup_data)

    # Authenticate a user
    access_token, refresh_token = await login(db_session, login_data)
    ```
"""
