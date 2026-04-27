import uuid
from datetime import datetime, timezone

import jwt

from app.auth.domain.ports.token_issuer import TokenClaims
from app.core.keys import RSAKeyPair


class JwtTokenIssuer:
    def __init__(self, key_pair: RSAKeyPair, algorithm: str, issuer: str) -> None:
        self._key_pair = key_pair
        self._algorithm = algorithm
        self._issuer = issuer

    def issue(self, claims: TokenClaims) -> str:
        now = datetime.now(timezone.utc)
        expire = now + claims.ttl
        payload = {
            "sub": str(claims.sub),
            "iss": self._issuer,
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
            "username": claims.username,
            "roles": claims.roles,
            "permissions": claims.permissions,
            "is_super_user": claims.is_super_user,
        }
        return jwt.encode(
            payload, self._key_pair.private_key, algorithm=self._algorithm
        )
