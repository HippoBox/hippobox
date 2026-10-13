from enum import StrEnum


class APIKeyRealtimeEventType(StrEnum):
    CREATED = "api_key.created"
    STATUS_UPDATED = "api_key.status_updated"
    DELETED = "api_key.deleted"
