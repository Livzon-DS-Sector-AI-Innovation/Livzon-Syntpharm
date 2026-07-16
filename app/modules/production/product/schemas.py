"""Product schemas for validation and serialization."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    workshop: str
    name: str
    description: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProductResponse(ProductBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
