import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import PaymentCreate
from app.models.outbox import Outbox, OutboxStatus
from app.models.payment import Payment, PaymentStatus


async def get_payment_by_id(db: AsyncSession, payment_id: str) -> Payment | None:
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    return result.scalar_one_or_none()


async def get_payment_by_idempotency_key(db: AsyncSession, key: str) -> Payment | None:
    result = await db.execute(select(Payment).where(Payment.idempotency_key == key))
    return result.scalar_one_or_none()


async def create_payment(
    db: AsyncSession, payment_data: PaymentCreate, idempotency_key: str
) -> Payment:
    payment = Payment(
        amount=payment_data.amount,
        currency=payment_data.currency,
        description=payment_data.description,
        metadata_=payment_data.metadata_,
        idempotency_key=idempotency_key,
        webhook_url=str(payment_data.webhook_url),
        status=PaymentStatus.pending,
    )
    db.add(payment)
    await db.flush()

    outbox_entry = Outbox(
        event_type="payment.new",
        payload={
            "payment_id": payment.id,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "webhook_url": payment.webhook_url,
        },
        status=OutboxStatus.pending,
    )
    db.add(outbox_entry)
    await db.commit()
    await db.refresh(payment)
    return payment
