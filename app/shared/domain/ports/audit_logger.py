import uuid
from typing import Any, Protocol


class AuditLogger(Protocol):
    """Port for writing audit events.

    Implementations join the caller's UoW so that the audit write commits
    atomically with the business state change that produced it.
    """

    async def log(
        self,
        actor_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        payload: dict[str, Any] | None = None,
    ) -> None: ...
