class DomainError(Exception):
    """Base class for all domain errors."""


class SystemRoleProtectedError(DomainError):
    """Raised when attempting to delete or mutate a protected (system) role."""

    def __init__(self) -> None:
        super().__init__("Cannot delete system role")
