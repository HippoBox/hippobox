from enum import Enum

from .error import (
    ServiceErrorCode,
    ServiceException,
    build_error_models,
    build_error_responses_from_codes,
)


class BillingErrorCode(Enum):
    BILLING_WEBHOOK_INVALID = ServiceErrorCode(
        "BILLING_WEBHOOK_INVALID", "Invalid billing webhook.", 400
    )
    BILLING_WEBHOOK_UNAVAILABLE = ServiceErrorCode(
        "BILLING_WEBHOOK_UNAVAILABLE", "Billing webhook is not configured.", 503
    )
    BILLING_DISABLED = ServiceErrorCode("BILLING_DISABLED", "Billing is not configured.", 503)
    BILLING_UNAVAILABLE = ServiceErrorCode(
        "BILLING_UNAVAILABLE", "Payment provider is temporarily unavailable.", 502
    )
    BILLING_PLAN_UNAVAILABLE = ServiceErrorCode(
        "BILLING_PLAN_UNAVAILABLE", "Subscription plan is not configured.", 503
    )
    BILLING_CHECKOUT_CONFLICT = ServiceErrorCode(
        "BILLING_CHECKOUT_CONFLICT",
        "An existing subscription or another checkout requires attention.",
        409,
    )
    BILLING_CHANGE_CONFLICT = ServiceErrorCode(
        "BILLING_CHANGE_CONFLICT", "Subscription changed. Refresh before confirming again.", 409
    )
    BILLING_METHOD_REQUIRED = ServiceErrorCode(
        "BILLING_METHOD_REQUIRED",
        "Choose another default payment method before removing this one.",
        409,
    )
    BILLING_NOT_FOUND = ServiceErrorCode("BILLING_NOT_FOUND", "Billing resource not found.", 404)
    BILLING_RECONCILIATION_REQUIRED = ServiceErrorCode(
        "BILLING_RECONCILIATION_REQUIRED", "Customer setup requires operator reconciliation.", 409
    )

    @property
    def code(self) -> ServiceErrorCode:
        return self.value


class BillingException(ServiceException):
    def __init__(self, code: BillingErrorCode):
        super().__init__(code=code.code)


BillingErrorDetail, BillingErrorResponse = build_error_models(
    detail_model_name="BillingErrorDetail",
    response_model_name="BillingErrorResponse",
    error_values=[item.code.error for item in BillingErrorCode],
    example_error="BILLING_DISABLED",
)


def billing_error_responses() -> dict[int, dict[str, object]]:
    return build_error_responses_from_codes(
        response_model=BillingErrorResponse, codes=[item.code for item in BillingErrorCode]
    )
