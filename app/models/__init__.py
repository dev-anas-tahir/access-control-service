"""
Database models for the access control service.

This package contains all SQLAlchemy models that represent the database
structure for the access control system, including users, roles, and permissions.

The models are organized to support:
- User management
- Role-based access control
- Permission-based authorization
- Soft delete functionality
- Timestamp tracking

Example:
    ```python
    from app.models.user import User
    from app.models.role import Role
    
    # Create a new user
    user = User(
    username="john_doe",
    email="john@example.com",
    password="securepassword"
    )
    
    # Assign a role to the user
    role = Role(name="admin")
    user.roles.append(role)
    ```
"""
