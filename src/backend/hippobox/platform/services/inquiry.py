from __future__ import annotations

from hippobox.platform.core.observability.service import observe_service
from hippobox.platform.models.inquiry import (
    INQUIRIES,
    InquiryCreate,
    InquiryDetail,
    InquiryPage,
    InquiryReply,
    InquiryStatus,
)
from hippobox.platform.services.inbox import InboxService


class InquiryService:
    async def _publish(self, recipients: list[int]) -> None:
        for user_id in recipients:
            await InboxService().changed(user_id)

    @observe_service("inquiries.list")
    async def list(
        self, user_id: int, admin: bool, page: int, page_size: int, status: InquiryStatus | None
    ) -> InquiryPage:
        return await INQUIRIES.list(user_id, admin, page, page_size, status)

    @observe_service("inquiries.detail")
    async def detail(self, inquiry_id: int, user_id: int, admin: bool) -> InquiryDetail:
        return await INQUIRIES.detail(inquiry_id, user_id, admin)

    @observe_service("inquiries.create")
    async def create(self, user_id: int, form: InquiryCreate) -> InquiryDetail:
        inquiry_id, recipients = await INQUIRIES.create(user_id, form)
        await self._publish(recipients)
        return await INQUIRIES.detail(inquiry_id, user_id, False)

    @observe_service("inquiries.reply")
    async def reply(
        self, inquiry_id: int, user_id: int, admin: bool, form: InquiryReply
    ) -> InquiryDetail:
        await self._publish(await INQUIRIES.reply(inquiry_id, user_id, admin, form))
        return await INQUIRIES.detail(inquiry_id, user_id, admin)

    @observe_service("inquiries.status")
    async def status(self, inquiry_id: int, user_id: int, status: InquiryStatus) -> InquiryDetail:
        await self._publish(await INQUIRIES.status(inquiry_id, user_id, status))
        return await INQUIRIES.detail(inquiry_id, user_id, True)
