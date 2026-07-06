import asyncio
import json

from sqlalchemy import select, update

from app.broker.rabbitmq import broker
from app.db.session import async_session_factory
from app.models.outbox import Outbox, OutboxStatus


async def outbox_poller(interval: float = 1):
    """
    Бесконечно опрашивает таблицу outbox, публикует pending-события в RabbitMQ.
    """
    while True:
        async with async_session_factory() as session:
            # Выбираем одну запись со статусом pending (можно пачку)
            result = await session.execute(
                select(Outbox)
                .where(Outbox.status == OutboxStatus.pending)
                .order_by(Outbox.created_at)
                .limit(10)  # обрабатываем до 10 за раз
            )
            entries = result.scalars().all()
            for entry in entries:
                try:
                    # Публикуем сообщение
                    await broker.publish(
                        entry.payload,
                        exchange="payments",
                        routing_key="new",
                    )
                    # Помечаем как processed
                    entry.status = OutboxStatus.processed
                    session.add(entry)
                except Exception as e:
                    # Логируем ошибку, запись останется pending для повторной попытки
                    print(f"Failed to publish outbox entry {entry.id}: {e}")
            await session.commit()
        await asyncio.sleep(interval)
