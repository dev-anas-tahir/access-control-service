"""
Core components for the access control service.

This package contains fundamental utilities and configurations used throughout
the access control service, including security utilities, dependencies, and
exception handling.

Components include:
- Security utilities for password hashing and token generation
- Dependency injection helpers
- Custom exception definitions
- Configuration management

Example:
    ```python
    from app.core.security import hash_password, create_access_token
    from app.core.exceptions import UniquenessError

    # Hash a password
    hashed = hash_password("my_password")

    # Create an access token
    token = create_access_token(user_id=1, username="john_doe", roles=["creator"],
    permissions=["read", "write"])
    ```
"""
