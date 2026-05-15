import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol


@dataclass
class TokenClaims:
    sub: uuid.UUID
    username: str
    roles: list[str]
    permissions: list[str]
    is_super_user: bool
    ttl: timedelta


class TokenIssuer(Protocol):
    def issue(self, claims: TokenClaims) -> str: ...
