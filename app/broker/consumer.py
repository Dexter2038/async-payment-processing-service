import asyncio
import logging
import random
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.broker.rabbitmq import broker
from app.config import settings
from app.db.session import async_session_factory
from app.models.payment import Payment, PaymentStatus

logger = logging.getLogger(__name__)


async def send_webhook(url: str, payment_id: str, status: str, processed_at: str):
    """Отправляет POST-уведомление на webhook URL."""
    payload = {
        "payment_id": payment_id,
        "status": status,
        "processed_at": processed_at,
    }
    async with httpx.AsyncClient(timeout=settings.webhook_timeout) as client:
        response = await client.post(url, json=payload)
        if response.status_code not in (200, 201, 202, 204):
            raise Exception(
                f"Webhook failed with status {response.status_code}: {response.text}"
            )
        logger.info(f"Webhook sent to {url} for payment {payment_id}")


async def publish_to_dlq(message: dict):
    """Публикует сообщение в Dead Letter Queue."""
    await broker.publish(
        message,
        exchange="payments.dlx",
        routing_key="dead",
    )
    logger.info(f"Message sent to DLQ: {message}")


@broker.subscriber("payments.new")
async def handle_payment(msg: dict):
    payment_id = msg.get("payment_id")
    if not payment_id:
        logger.error("No payment_id in message")
        return

    async with async_session_factory() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            logger.error(f"Payment {payment_id} not found")
            return

        if payment.webhook_sent:
            logger.info(f"Webhook already sent for payment {payment_id}, skipping")
            return

        # Эмуляция обработки только в статусе pending
        if payment.status == PaymentStatus.pending:
            delay = random.uniform(2, 5)
            await asyncio.sleep(delay)
            success = random.random() < 0.9
            if success:
                payment.status = PaymentStatus.succeeded
                logger.info(f"Payment {payment_id} succeeded")
            else:
                payment.status = PaymentStatus.failed
                logger.info(f"Payment {payment_id} failed")

            payment.processed_at = datetime.now(timezone.utc)
            session.add(payment)
            await session.commit()

            # Если webhook не был отправлен, пытаемся отправить с retry
            if not payment.webhook_sent:
                max_retries = 3
                backoff_base = 1
                for attempt in range(1, max_retries + 1):
                    try:
                        await send_webhook(
                            url=payment.webhook_url,
                            payment_id=payment.id,
                            status=payment.status.value,
                            processed_at=payment.processed_at.isoformat()
                            if payment.processed_at
                            else "",
                        )
                        payment.webhook_sent = True
                        session.add(payment)
                        await session.commit()
                        break
                    except Exception as e:
                        logger.warning(
                            f"Webhook attempt {attempt}/{max_retries} failed: {e}"
                        )
                        if attempt == max_retries:
                            await publish_to_dlq(msg)
                            return
                        await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))
