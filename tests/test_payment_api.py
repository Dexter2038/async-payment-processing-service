import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


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
