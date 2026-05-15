from pydantic import BaseModel, ConfigDict


class OrmSchema(BaseModel):
    """Base schema for models populated from ORM objects."""

    model_config = ConfigDict(from_attributes=True)
