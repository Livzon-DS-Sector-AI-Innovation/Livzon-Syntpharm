"""Attachment review Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AttachmentReviewOut(BaseModel):
    id: uuid.UUID
    deviation_id: uuid.UUID | None = None
    capa_id: uuid.UUID | None = None
    attachment_url: str
    reviewer_id: uuid.UUID
    review_time: datetime | None = None
    content: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateAttachmentReviewRequest(BaseModel):
    deviation_id: uuid.UUID | None = None
    capa_id: uuid.UUID | None = None
    attachment_url: str
    content: str
