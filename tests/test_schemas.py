from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas import PaymentCreate


def test_valid_payment_create():
    data = {
        "amount": "100.50",
        "currency": "USD",
        "description": "Test",
        "metadata": {"key": "value"},
        "webhook_url": "https://example.com/webhook",
    }
    payment = PaymentCreate(**data)
    assert payment.amount == Decimal("100.50")
    assert payment.metadata_ == {"key": "value"}


def test_invalid_currency_length():
    with pytest.raises(ValidationError):
        PaymentCreate(amount=100, currency="US", webhook_url="https://example.com")
