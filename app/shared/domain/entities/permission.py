import uuid
from dataclasses import dataclass


@dataclass
class Permission:
    id: uuid.UUID
    scope_key: str
    resource: str
    action: str
