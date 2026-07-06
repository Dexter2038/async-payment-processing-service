import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_no_auth_required():
    # Проверим, что /health пока без аутентификации работает (мы ещё не применяли зависимость)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_missing_api_key():
    # Тест для эндпоинта, который будет защищён (пока заглушка)
    # Мы добавим тестовый маршрут позже, но уже можно проверить логику зависимости.
    pass  # Пока пропустим, так как нет защищённого эндпоинта
