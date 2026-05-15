import jwt

from app.auth.domain.exceptions import InvalidTokenError, TokenExpiredError
from app.auth.domain.ports.token_verifier import TokenPayload
from app.auth.infrastructure.crypto.key_pair import RSAKeyPair


class JwtTokenVerifier:
    def __init__(self, key_pair: RSAKeyPair, algorithm: str) -> None:
        self._key_pair = key_pair
        self._algorithm = algorithm

    def verify(self, token: str) -> TokenPayload:
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
