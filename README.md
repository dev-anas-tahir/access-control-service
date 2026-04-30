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

The service follows **hexagonal (ports & adapters) architecture** across three bounded contexts:

- **Domain layer** — pure Python dataclasses and `typing.Protocol` ports; no SQLAlchemy, FastAPI, or Redis
- **Application layer** — one class per use case (`SignupUseCase`, `LoginUseCase`, `CreateRoleUseCase`, …) that depend only on ports
- **Infrastructure layer** — adapters: SQLAlchemy repositories, Redis stores, FastAPI routes, JWT crypto

```
app/
├── auth/        # Signup, login, refresh, logout — JWT + bcrypt
├── rbac/        # Roles, permissions, user-role assignments — RBAC
├── audit/       # Audit log reads
├── shared/      # Cross-cutting: entities, value objects, domain events, infra utils
└── core/        # Logging, middleware, context
```

Domain events decouple RBAC from Audit: use cases emit typed events (`RoleCreated`, `PermissionGranted`, …); the Unit of Work dispatches them to the audit logger after commit.

See [`docs/01-system-architecture.md`](docs/01-system-architecture.md) for the full architecture reference.

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

- `POST /api/v1/auth/signup` — Register a new user
- `POST /api/v1/auth/login` — Authenticate and receive access + refresh tokens
- `POST /api/v1/auth/logout` — Revoke tokens
- `POST /api/v1/auth/refresh` — Rotate refresh token
- `GET /api/v1/auth/me` — Current user info
- `GET /.well-known/jwks.json` — Public key for JWT verification
- `POST /api/v1/admin/roles` — Create role (super user only)
- `DELETE /api/v1/admin/roles/{id}` — Delete role
- `POST /api/v1/admin/roles/{id}/permissions` — Assign permission
- `DELETE /api/v1/admin/roles/{id}/permissions` — Revoke permission
- `POST /api/v1/admin/users/{id}/roles` — Assign role to user
- `DELETE /api/v1/admin/users/{id}/roles/{role_id}` — Revoke role from user
- `GET /api/v1/admin/audit-logs` — Paginated audit trail

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
