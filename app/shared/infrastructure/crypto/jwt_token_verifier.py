import jwt

from app.auth.infrastructure.crypto.key_pair import RSAKeyPair
from app.core.exceptions import InvalidTokenError, TokenExpiredError


class JwtTokenVerifier:
    def __init__(self, key_pair: RSAKeyPair, algorithm: str) -> None:
        self._key_pair = key_pair
        self._algorithm = algorithm

    def verify(self, token: str) -> dict[str, object]:
        try:
            return jwt.decode(
                token,
                self._key_pair.public_key,
                algorithms=[self._algorithm],
                options={"require": ["sub", "exp", "jti", "iss"]},
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {e}")
