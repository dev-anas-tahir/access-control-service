import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.infrastructure.orm.user import User as UserORM
from app.auth.infrastructure.repositories.mappers import (
    apply_domain_to_user_orm,
    user_orm_to_domain,
)
from app.rbac.infrastructure.orm.association import UserRole
from app.rbac.infrastructure.orm.role import Role as RoleORM
from app.shared.domain.entities.user import User


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        return select(UserORM).options(
            selectinload(UserORM.roles).selectinload(RoleORM.permissions)
        )

    async def find_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            self._base_query().where(UserORM.username == username)
        )
        orm = result.scalar_one_or_none()
        return user_orm_to_domain(orm) if orm else None

    async def find_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            self._base_query().where(UserORM.email == email)
        )
        orm = result.scalar_one_or_none()
        return user_orm_to_domain(orm) if orm else None

    async def find_by_id(self, id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            self._base_query().where(UserORM.id == id)
        )
        orm = result.scalar_one_or_none()
        return user_orm_to_domain(orm) if orm else None

    async def add(self, user: User) -> User:
        orm = UserORM(
            username=user.username,
            email=user.email.value if user.email else None,
            password_hash=user.password_hash,
            is_active=user.is_active,
            is_super_user=user.is_super_user,
            organization_id=user.organization_id,
        )
        self._session.add(orm)
        await self._session.flush()

        for role in user.roles:
            assoc = UserRole(user_id=orm.id, role_id=role.id)
            self._session.add(assoc)

        await self._session.flush()
        result = await self._session.execute(
            self._base_query().where(UserORM.id == orm.id)
        )
        orm = result.scalar_one()
        return user_orm_to_domain(orm)

    async def update(self, user: User) -> None:
        result = await self._session.execute(
            select(UserORM).where(UserORM.id == user.id)
        )
        orm = result.scalar_one()
        apply_domain_to_user_orm(user, orm)
        self._session.add(orm)
