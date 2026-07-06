from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key
from app.api.v1.schemas import PaymentCreate, PaymentDetail, PaymentResponse
from app.db.session import get_async_session
from app.services.payment_service import (
    create_payment,
    get_payment_by_id,
    get_payment_by_idempotency_key,
)

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a payment",
)
async def create_payment_endpoint(
    payment_data: PaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_async_session),
):
    # Проверяем идемпотентность
    existing = await get_payment_by_idempotency_key(db, idempotency_key)
    if existing:
        return PaymentResponse(
            payment_id=existing.id,
            status=existing.status,
            created_at=existing.created_at,
        )

    payment = await create_payment(db, payment_data, idempotency_key)
    return PaymentResponse(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentDetail,
    summary="Get payment details",
)
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    payment = await get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment
