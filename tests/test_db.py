import pytest

from app.db.session import async_session_factory, engine


@pytest.mark.asyncio
async def test_engine_creation():
    assert engine is not None
    assert engine.url.database == "payments"  # из DATABASE_URL по умолчанию


@pytest.mark.asyncio
async def test_session_factory():
    # Проверяем, что фабрика создаёт асинхронную сессию
    async with async_session_factory() as session:
        assert session is not None
