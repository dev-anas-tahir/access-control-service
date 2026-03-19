"""
Integration tests for JWKS endpoint.

Tests the /.well-known/jwks.json endpoint that serves the public key.
"""

from unittest.mock import patch

from httpx import AsyncClient, Response


async def test_jwks_endpoint_returns_valid_jwks(client: AsyncClient):
    """Test that the JWKS endpoint returns a valid JSON Web Key Set."""
    response: Response = await client.get("/.well-known/jwks.json")

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "keys" in data
    assert isinstance(data["keys"], list)
    assert len(data["keys"]) == 1

    jwk = data["keys"][0]

    # Verify required JWK fields
    assert "kty" in jwk
    assert jwk["kty"] == "RSA"

    assert "use" in jwk
    assert jwk["use"] == "sig"

    assert "kid" in jwk
    assert isinstance(jwk["kid"], str)
    assert len(jwk["kid"]) > 0

    assert "alg" in jwk
    assert jwk["alg"] == "RS256"

    assert "n" in jwk
    assert isinstance(jwk["n"], str)
    assert len(jwk["n"]) > 0

    assert "e" in jwk
    assert isinstance(jwk["e"], str)
    assert len(jwk["e"]) > 0


async def test_jwks_endpoint_consistent_kid(client: AsyncClient):
    """Test that the key ID (kid) is consistent across multiple requests."""
    response1: Response = await client.get("/.well-known/jwks.json")
    response2: Response = await client.get("/.well-known/jwks.json")

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # The kid should be the same for the same public key
    assert data1["keys"][0]["kid"] == data2["keys"][0]["kid"]


async def test_jwks_endpoint_base64url_encoding(client: AsyncClient):
    """Test that the modulus (n) and exponent (e) are properly base64url-encoded."""
    response: Response = await client.get("/.well-known/jwks.json")

    assert response.status_code == 200
    data = response.json()

    jwk = data["keys"][0]

    # Base64url encoding should not contain padding characters (=)
    assert "=" not in jwk["n"]
    assert "=" not in jwk["e"]

    # Should only contain URL-safe characters (alphanumeric, - and _)
    import re

    base64url_pattern = re.compile(r"^[A-Za-z0-9\-_]+$")
    assert base64url_pattern.match(jwk["n"])
    assert base64url_pattern.match(jwk["e"])


async def test_jwks_endpoint_error_handling(client: AsyncClient):
    """Test that the JWKS endpoint handles errors gracefully."""
    # Mock the key_pair to simulate an error
    with patch("app.api.v1.jwks.key_pair") as mock_key_pair:
        # Make public_key property raise an exception
        type(mock_key_pair).public_key = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("Key error"))
        )

        response: Response = await client.get("/.well-known/jwks.json")

        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to retrieve public key" in data["detail"]
