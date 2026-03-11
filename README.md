# Access Control Service

A comprehensive access control system built with FastAPI, SQLAlchemy, and Pydantic that provides role-based authentication and authorization.

## Features

- **User Management**: Secure user registration, authentication, and profile management
- **Role-Based Access Control (RBAC)**: Flexible role assignment and management
- **Token Authentication**: JWT-based authentication with refresh token rotation
- **Fine-Grained Permissions**: Resource and action-based permission system
- **Database Integration**: Asynchronous PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis integration for token management and caching
- **Event Streaming**: Google Cloud Pub/Sub for audit logging and notifications

## Architecture

The service follows a clean architecture pattern with distinct layers:

- **Models**: SQLAlchemy models for database entities
- **Schemas**: Pydantic models for data validation and serialization
- **Services**: Business logic implementations
- **Core**: Shared utilities and configurations
- **DB**: Database and cache utilities

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd access-control-service
```

2. Install dependencies:
```bash
uv venv
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Generate RSA keys for JWT:
```bash
mkdir keys
openssl genrsa -out keys/private_key.pem 2048
openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem
```

5. Run database migrations:
```bash
alembic upgrade head
```

## Usage

Start the application:
```bash
uvicorn app.main:app --reload
```

The API documentation will be available at `http://localhost:8000/docs`.

## API Endpoints

- `POST /auth/signup` - Register a new user
- `POST /auth/login` - Authenticate a user
- `POST /auth/logout` - Log out a user
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user information

## Documentation Standards

This project follows Python documentation best practices:

- **Google Style Docstrings**: Used throughout the codebase for consistency
- **Type Hints**: Comprehensive type annotations for all functions and variables
- **Module Documentation**: Each module includes a descriptive docstring
- **Class Documentation**: All classes have detailed docstrings explaining their purpose
- **Function Documentation**: All public functions include parameter, return, and exception documentation
- **Examples**: Code examples included where helpful

## Technologies

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and Object Relational Mapper
- **Pydantic**: Data validation and settings management
- **Redis**: In-memory data structure store
- **PostgreSQL**: Advanced open-source database
- **JWT**: Secure token-based authentication
- **Google Cloud Pub/Sub**: Messaging service for event streaming

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with proper documentation
4. Submit a pull request

## License

This project is licensed under the MIT License.
