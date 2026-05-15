"""
Access Control Service - Main Application Package.

This package implements a comprehensive access control system with role-based
authentication and authorization. The service provides secure user management,
token-based authentication, and fine-grained permission controls.

The application is structured into several modules:
- core: Fundamental utilities and configurations
- models: SQLAlchemy database models
- schemas: Pydantic data validation schemas
- services: Business logic implementations
- db: Database and cache utilities

Example:
    ```python
    from app.main import app

    # Run the application
    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    ```
"""
