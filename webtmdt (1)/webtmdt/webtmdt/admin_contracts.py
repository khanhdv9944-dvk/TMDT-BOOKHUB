"""Transport contracts for Admin workflows that are not persisted yet.

These schemas document the API boundary used by the frontend mock services.
They intentionally do not imply that the corresponding database tables exist.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class DisputeStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    WAITING_SELLER = "WAITING_SELLER"
    WAITING_BUYER = "WAITING_BUYER"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class DisputeDecision(str, Enum):
    REFUND_BUYER = "REFUND_BUYER"
    RESOLVE_FOR_SELLER = "RESOLVE_FOR_SELLER"


class DisputeAction(BaseModel):
    note: Optional[str] = None


class DisputeRejection(BaseModel):
    reason: str = Field(min_length=1)


class PayoutStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class PayoutRejection(BaseModel):
    reason: str = Field(min_length=1)


class DocumentType(str, Enum):
    BUSINESS_LICENSE = "BUSINESS_LICENSE"
    IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT"
    TAX_DOCUMENT = "TAX_DOCUMENT"
    OTHER = "OTHER"


class DocumentContract(BaseModel):
    id: str
    owner_id: int | str
    type: DocumentType
    file_name: str
    mime_type: str
    file_url: Optional[str] = None
    uploaded_at: datetime
    status: str


class PermissionUpdate(BaseModel):
    permissions: list[str]


class AuditLogContract(BaseModel):
    id: str
    actor_id: int | str
    action: str
    target_type: str
    target_id: int | str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
