from fastapi import APIRouter, Depends, Request

from hippobox.platform.core.error.billing_exception import (
    BillingErrorCode,
    BillingException,
    billing_error_responses,
)
from hippobox.platform.services.billing_notifications import BillingNotificationService

router = APIRouter()


@router.post("/webhook", responses=billing_error_responses())
async def billing_webhook(
    request: Request, service: BillingNotificationService = Depends(BillingNotificationService)
) -> dict[str, str]:
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > 262144:
            raise BillingException(BillingErrorCode.BILLING_WEBHOOK_INVALID)
    await service.receive(bytes(payload), request.headers.get("stripe-signature", ""))
    return {"status": "received"}
