""" """

import base64
import hashlib
import logging

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import APIRouter, HTTPException, status

from app.core.keys import key_pair

logger = logging.getLogger(__name__)

router = APIRouter(tags=["jwks"])


def to_base64url(n: int) -> str:
    """Convert an integer to a base64url-encoded string without padding."""
    byte_length = (n.bit_length() + 7) // 8
    return (
        base64.urlsafe_b64encode(n.to_bytes(byte_length, byteorder="big"))
        .rstrip(b"=")
        .decode()
    )


@router.get("/.well-known/jwks.json")
async def jwks():
    """
    Endpoint to serve the JSON Web Key Set (JWKS) containing the public key used for
    verifying JWTs. This allows clients to retrieve the public key and use it to verify
    the signatures of JWTs issued by the authentication service.
    """
    try:
        public_key = key_pair.public_key
        numbers = public_key.public_numbers()
        pub_bytes = public_key.public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )
        kid = hashlib.sha256(pub_bytes).hexdigest()[:16]
        n = to_base64url(numbers.n)
        e = to_base64url(numbers.e)
        kid = "my-key-id"
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "kid": kid,
            "alg": "RS256",
            "n": n,
            "e": e,
        }
        return {"keys": [jwk]}
    except Exception as e:
        logger.error(f"Failed to retrieve public key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve public key",
        )
