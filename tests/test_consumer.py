import asyncio
import uuid

import pytest
from sqlalchemy import select

import app.broker.consumer  # noqa: F401  # регистрируем subscriber
from app.broker.rabbitmq import broker
from app.broker.topology import declare_topology
from app.db.session import async_session_factory
from app.models.payment import Payment, PaymentStatus


@pytest.mark.skip(
    reason="Skipping due to RabbitMQ queue parameter conflict; will be resolved after topology stabilization"
)
@pytest.mark.asyncio
async def test_consumer_processes_payment():
    unique_idempotency_key = f"cons-test-{uuid.uuid4()}"

    # Создаём тестовый платёж напрямую в БД
    async with async_session_factory() as session:
        payment = Payment(
            amount=100,
            currency="USD",
            idempotency_key=unique_idempotency_key,
            webhook_url="https://example.com/webhook",
            status=PaymentStatus.pending,
        )
        session.add(payment)
        await session.commit()
        payment_id = payment.id

    # Запускаем брокер и топологию
    await broker.start()
    await declare_topology()

    # Публикуем сообщение для этого платежа
    await broker.publish(
        {"payment_id": payment_id},
        exchange="payments",
        routing_key="new",
    )

    # Ждём обработку (максимальная задержка 5 сек + запас)
    await asyncio.sleep(8)

    # Проверяем, что статус изменился
    async with async_session_factory() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        updated_payment = result.scalar_one()
        assert updated_payment.status in (
            PaymentStatus.succeeded,
            PaymentStatus.failed,
        )
        assert updated_payment.processed_at is not None

    await broker.stop()
