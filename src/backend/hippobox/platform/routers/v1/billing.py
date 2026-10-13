from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response, status

from hippobox.platform.core.error.billing_exception import billing_error_responses
from hippobox.platform.core.error.response_contracts import current_user_error_responses
from hippobox.platform.deps import get_current_user
from hippobox.platform.models.billing import (
    BillingCardSetupResponse,
    BillingCardSetupStatus,
    BillingChangeForm,
    BillingCheckoutForm,
    BillingCheckoutStatusResponse,
    BillingConfigResponse,
    BillingInvoiceDetail,
    BillingInvoicesResponse,
    BillingMethodForm,
    BillingPaymentMethodsResponse,
    BillingPlansResponse,
    BillingPortalForm,
    BillingProfileForm,
    BillingProfileResponse,
    BillingSetupForm,
    BillingSetupResponse,
    BillingSetupStatusResponse,
    BillingSubscriptionResponse,
)
from hippobox.platform.models.user import UserResponse
from hippobox.platform.services.billing import BillingService


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    dependencies=[Depends(no_store)],
    responses=current_user_error_responses(
        billing_error_responses(),
    ),
)


@router.get("/config", response_model=BillingConfigResponse)
async def billing_config(
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingConfigResponse:
    return service.config()


@router.post(
    "/setup-sessions", response_model=BillingSetupResponse, status_code=status.HTTP_201_CREATED
)
async def create_setup(
    form: BillingSetupForm,
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingSetupResponse:
    return await service.create_setup(current_user.id, form)


@router.get("/setup-sessions/{session_id}", response_model=BillingSetupStatusResponse)
async def setup_status(
    session_id: Annotated[str, Path(pattern=r"^cs_[A-Za-z0-9_]+$", max_length=255)],
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingSetupStatusResponse:
    return await service.setup_status(current_user.id, session_id)


@router.get("/payment-methods", response_model=BillingPaymentMethodsResponse)
async def list_payment_methods(
    method_type: Literal["card", "link"] = "card",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    starting_after: Annotated[
        str | None, Query(pattern=r"^pm_[A-Za-z0-9]+$", max_length=255)
    ] = None,
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingPaymentMethodsResponse:
    return await service.list_payment_methods(current_user.id, method_type, limit, starting_after)


@router.get("/plans", response_model=BillingPlansResponse)
async def plans(
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingPlansResponse:
    return await service.plans()


@router.get("/subscription", response_model=BillingSubscriptionResponse)
async def subscription(
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingSubscriptionResponse:
    return await service.subscription(current_user.id)


@router.post(
    "/checkout-sessions", response_model=BillingSetupResponse, status_code=status.HTTP_201_CREATED
)
async def create_checkout(
    form: BillingCheckoutForm,
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingSetupResponse:
    return await service.create_checkout(current_user.id, form)


@router.get("/checkout-sessions/{session_id}", response_model=BillingCheckoutStatusResponse)
async def checkout_status(
    session_id: Annotated[str, Path(pattern=r"^cs_[A-Za-z0-9_]+$", max_length=255)],
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingCheckoutStatusResponse:
    return await service.checkout_status(current_user.id, session_id)


@router.post("/subscription/change", response_model=BillingSubscriptionResponse)
async def change_subscription(
    form: BillingChangeForm,
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingSubscriptionResponse:
    return await service.change_subscription(current_user.id, form)


@router.get("/profile", response_model=BillingProfileResponse)
async def billing_profile(
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingProfileResponse:
    return await service.profile(current_user.id)


@router.get("/invoices", response_model=BillingInvoicesResponse)
async def billing_invoices(
    limit: Annotated[int, Query(ge=1, le=100)] = 4,
    starting_after: Annotated[
        str | None, Query(pattern=r"^in_[A-Za-z0-9]+$", max_length=255)
    ] = None,
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingInvoicesResponse:
    return await service.invoices(current_user.id, limit, starting_after)


@router.get("/invoices/{invoice_id}", response_model=BillingInvoiceDetail)
async def invoice_detail(
    invoice_id: Annotated[str, Path(pattern=r"^in_[A-Za-z0-9]+$", max_length=255)],
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingInvoiceDetail:
    return await service.invoice_detail(current_user.id, invoice_id)


@router.post(
    "/portal-sessions", response_model=BillingSetupResponse, status_code=status.HTTP_201_CREATED
)
async def billing_portal(
    form: BillingPortalForm,
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingSetupResponse:
    return await service.portal(current_user.id, form)


@router.put("/profile", response_model=BillingProfileResponse)
async def update_billing_profile(
    form: BillingProfileForm,
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingProfileResponse:
    return await service.update_profile(current_user.id, form)


@router.post("/payment-methods/{method_id}", response_model=BillingProfileResponse)
async def manage_billing_method(
    method_id: Annotated[str, Path(pattern=r"^pm_[A-Za-z0-9]+$", max_length=255)],
    form: BillingMethodForm,
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingProfileResponse:
    return await service.manage_method(current_user.id, method_id, form)


@router.post("/card-setups", response_model=BillingCardSetupResponse, status_code=201)
async def create_card_setup(
    form: BillingSetupForm,
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingCardSetupResponse:
    return await service.create_card_setup(current_user.id, form)


@router.get("/card-setups/{intent_id}", response_model=BillingCardSetupStatus)
async def card_setup_status(
    intent_id: Annotated[str, Path(pattern=r"^seti_[A-Za-z0-9]+$", max_length=255)],
    current_user: UserResponse = Depends(get_current_user),
    service: BillingService = Depends(BillingService),
) -> BillingCardSetupStatus:
    return await service.card_setup_status(current_user.id, intent_id)
