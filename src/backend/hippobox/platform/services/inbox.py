from __future__ import annotations

from hippobox.platform.core.error.inbox_exception import InboxErrorCode, InboxException
from hippobox.platform.core.observability.service import observe_service
from hippobox.platform.core.realtime.domain_events.inbox import InboxRealtimeEventType
from hippobox.platform.models.inbox import INBOX, InboxItem, InboxPage, InboxSummary
from hippobox.platform.services.realtime import RealtimeService


class InboxService:
    @observe_service("inbox.list")
    async def list(self, user_id: int, page: int, page_size: int, unread_only: bool) -> InboxPage:
        return await INBOX.list(user_id, page, page_size, unread_only)

    @observe_service("inbox.summary")
    async def summary(self, user_id: int) -> InboxSummary:
        return await INBOX.summary(user_id)

    @observe_service("inbox.read")
    async def read(self, user_id: int, notification_id: int) -> InboxItem:
        item = await INBOX.read(user_id, notification_id)
        if item is None:
            raise InboxException(InboxErrorCode.NOT_FOUND)
        await self.changed(user_id)
        return item

    @observe_service("inbox.read_all")
    async def read_all(self, user_id: int, through_id: int) -> InboxSummary:
        await INBOX.read_all(user_id, through_id)
        await self.changed(user_id)
        return await INBOX.summary(user_id)

    @observe_service("inbox.update_selected")
    async def update_selected(
        self, user_id: int, notification_ids: list[int], *, remove: bool
    ) -> InboxSummary:
        await INBOX.update_selected(user_id, notification_ids, remove=remove)
        await self.changed(user_id)
        return await INBOX.summary(user_id)

    async def changed(self, user_id: int) -> None:
        await RealtimeService().publish_user_notification(
            user_id=user_id, event_type=InboxRealtimeEventType.CHANGED
        )
