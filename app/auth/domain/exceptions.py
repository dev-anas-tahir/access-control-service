from typing import Literal

from app.shared.domain.exceptions import DomainError


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Invalid username or password")


class RefreshTokenInvalidError(DomainError):
    def __init__(self) -> None:
        super().__init__("Invalid or expired refresh token")


class DefaultRoleMissingError(DomainError):
    def __init__(self) -> None:
        super().__init__("Default 'viewer' role not found. Run seed script first.")


class UserExistsError(DomainError):
    def __init__(self, field: Literal["username", "email"]) -> None:
        self.field = field
        super().__init__(f"{field.capitalize()} already exists")
