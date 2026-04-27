from passlib.context import CryptContext

_pwd_context = CryptContext(
    schemes=["bcrypt", "django_pbkdf2_sha256"], deprecated="auto"
)


class BcryptPasswordHasher:
    def hash(self, plain: str) -> str:
        return _pwd_context.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        return _pwd_context.verify(plain, hashed)

    def needs_rehash(self, hashed: str) -> bool:
        return _pwd_context.needs_update(hashed)
