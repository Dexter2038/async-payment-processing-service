import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.config import settings
from app.db.session import async_session_factory
from app.main import app
from app.models.outbox import Outbox, OutboxStatus
from app.models.payment import Payment, PaymentStatus


@pytest.mark.asyncio
async def test_create_payment_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/payments",
            json={
                "amount": "100.00",
                "currency": "USD",
                "webhook_url": "https://example.com/webhook",
            },
            headers={
                "X-API-Key": settings.api_key,
                "Idempotency-Key": "test-key-002",
            },
        )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert "payment_id" in data


@pytest.mark.asyncio
async def test_idempotency():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {
            "X-API-Key": settings.api_key,
            "Idempotency-Key": "test-key-003",
        }
        payload = {
            "amount": "50.00",
            "currency": "EUR",
            "webhook_url": "https://example.com/webhook",
        }
        resp1 = await client.post("/api/v1/payments", json=payload, headers=headers)
        resp2 = await client.post("/api/v1/payments", json=payload, headers=headers)
    assert resp1.status_code == 202
    assert resp2.status_code == 202
    assert resp1.json()["payment_id"] == resp2.json()["payment_id"]


@pytest.mark.asyncio
async def test_get_payment_success():
    # Создаём тестовый платёж напрямую в БД
    async with async_session_factory() as session:
        payment = Payment(
            amount=Decimal("75.00"),
            currency="RUB",
            description="GET test",
            idempotency_key=f"test-get-{uuid.uuid4()}",
            webhook_url="https://example.com/webhook",
            status=PaymentStatus.pending,
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        payment_id = payment.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/payments/{payment_id}",
            headers={"X-API-Key": settings.api_key},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == payment_id
    assert data["amount"] == "75.00"
    assert data["currency"] == "RUB"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_payment_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/payments/nonexistent-id",
            headers={"X-API-Key": settings.api_key},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_payment_writes_to_outbox():
    # Используем уникальный idempotency_key, чтобы не мешать другим тестам
    unique_key = f"outbox-test-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/payments",
            json={
                "amount": "30.00",
                "currency": "USD",
                "webhook_url": "https://example.com/webhook",
            },
            headers={
                "X-API-Key": settings.api_key,
                "Idempotency-Key": unique_key,
            },
        )
    assert response.status_code == 202
    payment_id = response.json()["payment_id"]

    # Проверяем наличие записи в Outbox напрямую через сессию
    async with async_session_factory() as session:
        result = await session.execute(
            select(Outbox).where(Outbox.payload["payment_id"].as_string() == payment_id)
        )
        outbox_entry = result.scalar_one_or_none()
        assert outbox_entry is not None
        assert outbox_entry.event_type == "payment.new"
        assert outbox_entry.status == OutboxStatus.pending
        assert outbox_entry.payload["payment_id"] == payment_id
