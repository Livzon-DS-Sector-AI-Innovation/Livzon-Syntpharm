"""Product schemas for validation and serialization."""

import uuid
from datetime import datetime
from typing import Any

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


# ========== API Response Wrappers ==========


class ProductApiResponse(BaseModel):
    """Product response wrapper"""

    code: int = 200
    message: str = "success"
    data: ProductResponse | None = None


class ProductListApiResponse(BaseModel):
    """Product list response wrapper"""

    code: int = 200
    message: str = "success"
    data: list[ProductResponse]
    meta: dict[str, Any] | None = None
