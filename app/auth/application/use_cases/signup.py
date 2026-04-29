import uuid
from datetime import datetime

from app.auth.application.dto import SignupInput, SignupResult
from app.auth.domain.exceptions import DefaultRoleMissingError, UserExistsError
from app.auth.domain.ports.password_hasher import PasswordHasher
from app.auth.domain.ports.unit_of_work import AuthUnitOfWorkFactory
from app.shared.domain.entities.user import User
from app.shared.domain.values.email import Email


class SignupUseCase:
    def __init__(
        self,
        uow_factory: AuthUnitOfWorkFactory,
        hasher: PasswordHasher,
        default_role_name: str = "viewer",
    ) -> None:
        self._uow_factory = uow_factory
        self._hasher = hasher
        self._default_role_name = default_role_name

    async def execute(self, input: SignupInput) -> SignupResult:
        async with self._uow_factory() as uow:
            if await uow.users.find_by_username(input.username):
                raise UserExistsError("username")

            if input.email:
                if await uow.users.find_by_email(input.email):
                    raise UserExistsError("email")

            password_hash = self._hasher.hash(input.password)

            viewer_role = await uow.roles.find_by_name(self._default_role_name)
            if not viewer_role:
                raise DefaultRoleMissingError()

            new_user = User(
                id=uuid.uuid4(),
                username=input.username,
                email=Email(input.email) if input.email else None,
                password_hash=password_hash,
                is_active=True,
                is_super_user=False,
                roles=[viewer_role],
                created_at=datetime.now(),
            )
            persisted = await uow.users.add(new_user)
            await uow.commit()

        return SignupResult(
            id=persisted.id,
            username=persisted.username,
            email=persisted.email.value if persisted.email else None,
            created_at=persisted.created_at,
        )
