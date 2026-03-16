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
    # 1. Calculate the byte length needed to represent the integer
    byte_length = (n.bit_length() + 7) // 8

    # 2. Convert the integer to bytes and encode as base64url without padding
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
        # 1. Get the public key from the key pair
        public_key = key_pair.public_key

        # 2. Extract the public key numbers (modulus and exponent)
        numbers = public_key.public_numbers()

        # 3. Generate the key ID by hashing the DER-encoded public key
        pub_bytes = public_key.public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )
        kid = hashlib.sha256(pub_bytes).hexdigest()[:16]

        # 4. Convert the modulus and exponent to base64url format
        n = to_base64url(numbers.n)
        e = to_base64url(numbers.e)

        # 5. Override the key ID with a fixed value (temporary solution)
        kid = "my-key-id"

        # 6. Construct the JSON Web Key (JWK) with required fields
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "kid": kid,
            "alg": "RS256",
            "n": n,
            "e": e,
        }

        # 7. Return the JWKS with the constructed key
        return {"keys": [jwk]}
    except Exception as e:
        logger.error(f"Failed to retrieve public key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve public key",
        )
