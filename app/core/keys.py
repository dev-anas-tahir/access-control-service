from pathlib import Path

from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
)


class RSAKeyPair:
    """Class to manage RSA key pairs for signing and verification of JWTs"""
    def __init__(self):
        """Initialize the RSAKeyPair with no keys loaded"""
        self._private_key = None
        self._public_key = None

    def load(self, private_key_path: Path, public_key_path: Path):
        """Load the RSA key pair from the specified file paths"""
        with private_key_path.open("rb") as private_key_file:
            self._private_key = load_pem_private_key(
                private_key_file.read(), password=None
            )

        with public_key_path.open("rb") as public_key_file:
            self._public_key = load_pem_public_key(public_key_file.read())
    
    def rotate(self, private_key_path: Path, public_key_path: Path):
        """Rotate the RSA key pair by loading new keys from the specified paths"""
        with private_key_path.open("rb") as f:
            new_private = load_pem_private_key(f.read(), password=None)
        with public_key_path.open("rb") as f:
            new_public = load_pem_public_key(f.read())

        self._private_key = new_private
        self._public_key = new_public
    
    @property
    def private_key(self):
        """Return the loaded private key, or raise an error if not loaded"""
        if self._private_key is None:
            raise RuntimeError("Private key not loaded.")
        return self._private_key
    
    @property
    def public_key(self):
        """Return the loaded public key, or raise an error if not loaded"""
        if self._public_key is None:
            raise RuntimeError("Public key not loaded.")
        return self._public_key

key_pair = RSAKeyPair()
