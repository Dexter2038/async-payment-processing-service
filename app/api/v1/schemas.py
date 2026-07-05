from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, Field

from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)
    description: str | None = Field(None, max_length=255)
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    webhook_url: AnyHttpUrl


class PaymentResponse(BaseModel):
    payment_id: str
    status: PaymentStatus
    created_at: datetime


class PaymentDetail(BaseModel):
    id: str
    amount: Decimal
    currency: str
    description: str | None
    metadata: dict[str, Any] | None = Field(None, alias="metadata_")
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}
