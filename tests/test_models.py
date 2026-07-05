from decimal import Decimal

import pytest

from app.models.payment import Payment, PaymentStatus


def test_create_payment():
    payment = Payment(
        amount=Decimal("100.00"),
        currency="USD",
        description="Test payment",
        metadata_={"key": "value"},
        idempotency_key="test-key-123",
        webhook_url="https://example.com/webhook",
        status=PaymentStatus.pending,
    )
    assert payment.amount == Decimal("100.00")
    assert payment.currency == "USD"
    assert payment.status == PaymentStatus.pending
    assert payment.metadata_ == {"key": "value"}
    assert payment.processed_at is None
