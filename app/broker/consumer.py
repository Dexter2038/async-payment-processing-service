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

        if payment.status != PaymentStatus.pending:
            logger.info(
                f"Payment {payment_id} already processed, status={payment.status}"
            )
            return

        # Эмуляция обработки платежа
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

        # Отправляем webhook
        await send_webhook(
            url=payment.webhook_url,
            payment_id=payment.id,
            status=payment.status.value,
            processed_at=payment.processed_at.isoformat()
            if payment.processed_at is not None
            else datetime.utcnow().isoformat(),
        )
