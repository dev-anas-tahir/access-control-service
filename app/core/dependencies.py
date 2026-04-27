# Re-export shim — canonical definitions are in app.auth.infrastructure.http.dependencies.
# TODO: Remove this file when rbac/audit contexts are migrated to hexagonal.
from app.auth.infrastructure.http.dependencies import (  # noqa: F401
    get_current_user,
    require_super_user,
)
