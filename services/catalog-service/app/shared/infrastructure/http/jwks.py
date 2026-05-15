"""JWKS client that fetches and caches IAM's public key at startup."""

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from app.config import settings


class JwksClient:
    """Fetches the RS256 public key from IAM's JWKS endpoint and caches it."""

    def __init__(self) -> None:
        self._public_key: object | None = None

    async def load(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.iam_jwks_url, timeout=10)
            response.raise_for_status()
            jwks = response.json()

        # Pick first RS256 key
        for key in jwks.get("keys", []):
            if key.get("alg") == "RS256" or key.get("kty") == "RSA":
                self._public_key = RSAAlgorithm.from_jwk(key)
                return

        raise RuntimeError(f"No RSA key found in JWKS at {settings.iam_jwks_url}")

    @property
    def public_key(self) -> object:
        if self._public_key is None:
            raise RuntimeError("JWKS not loaded — call load() at startup")
        return self._public_key

    def verify(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                options={"require": ["sub", "exp", "jti", "iss"]},
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")


jwks_client = JwksClient()
