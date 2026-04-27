from app.shared.domain.exceptions import DomainError


class RoleAlreadyExistsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Role name already exists")


class RoleNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Role not found")


class SystemRoleProtectedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Cannot delete system role")


class PermissionAlreadyAssignedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Permission already assigned")


class PermissionNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Permission not found")


class UserNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("User not found")
