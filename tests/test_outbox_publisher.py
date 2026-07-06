import asyncio

import pytest
from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue
from sqlalchemy import select

from app.broker.rabbitmq import broker
from app.db.session import async_session_factory
from app.models.outbox import Outbox, OutboxStatus
from app.services.outbox_publisher import outbox_poller


@pytest.mark.asyncio
async def test_outbox_poller_publishes_and_updates_status():
    # Создадим запись Outbox напрямую
    async with async_session_factory() as session:
        entry = Outbox(
            event_type="payment.new",
            payload={"payment_id": "test-123"},
            status=OutboxStatus.pending,
        )
        session.add(entry)
        await session.commit()
        entry_id = entry.id

    # Запускаем брокер
    await broker.start()

    # Объявляем обменник и очередь через broker, получаем aio-pika объекты
    exchange = RabbitExchange("payments", type=ExchangeType.TOPIC)
    queue = RabbitQueue("payments.new", routing_key="new")
    rb_exchange = await broker.declare_exchange(exchange)
    rb_queue = await broker.declare_queue(queue)

    # Привязываем очередь к обменнику
    await rb_queue.bind(rb_exchange, routing_key="new")

    # Запускаем poller в фоновой задаче с интервалом 0.5 секунды
    poll_task = asyncio.create_task(outbox_poller(interval=0.5))
    await asyncio.sleep(1.5)  # даём время на обработку
    poll_task.cancel()
    try:
        await poll_task
    except asyncio.CancelledError:
        pass

    # Проверяем, что запись обработана
    async with async_session_factory() as session:
        result = await session.execute(select(Outbox).where(Outbox.id == entry_id))
        updated_entry = result.scalar_one()
        assert updated_entry.status == OutboxStatus.processed

    # Останавливаем брокер
    await broker.stop()
