from pydantic import BaseModel


class DomainEvent(BaseModel):
    event_type: str
    service: str
