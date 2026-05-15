import uuid
from dataclasses import dataclass

from app.shared.domain.values.scope_key import ScopeKey


@dataclass
class Permission:
    id: uuid.UUID
    scope_key: ScopeKey
