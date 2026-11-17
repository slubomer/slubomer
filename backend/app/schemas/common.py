"""Schemas reused by several endpoints."""

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Base for all response models: can be built straight from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    """One page of a list endpoint."""

    items: list[T]
    total: int
    page: int
    page_size: int
