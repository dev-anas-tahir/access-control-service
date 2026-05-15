import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Category:
    id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None = None
    created_at: datetime | None = None
