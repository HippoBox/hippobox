"""Provider-neutral, private object I/O contracts. Authorization belongs to domains."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class StorageErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"
    ACCESS_DENIED = "access_denied"
    UNAVAILABLE = "unavailable"
    TOO_LARGE = "too_large"
    CORRUPT_OBJECT = "corrupt_object"
    CLOSED = "closed"


class StorageError(Exception):
    """Sanitized infrastructure error; services map it to their domain exception."""

    def __init__(self, code: StorageErrorCode):
        self.code = code
        super().__init__(f"Object storage operation failed: {code.value}.")


@dataclass(frozen=True)
class ObjectMetadata:
    key: str
    size: int
    content_type: str


@dataclass(frozen=True)
class StoredObject:
    metadata: ObjectMetadata
    data: bytes


def validate_key(key: str) -> None:
    # Portable canonical subset: no URL encoding, filesystem escapes or empty segments.
    if (
        not isinstance(key, str)
        or len(key) > 512
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", key)
        or any(segment in ("", ".", "..") for segment in key.split("/"))
    ):
        raise StorageError(StorageErrorCode.INVALID_INPUT)


def validate_content_type(content_type: str) -> None:
    if len(content_type) > 255 or not re.fullmatch(
        r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+", content_type
    ):
        raise StorageError(StorageErrorCode.INVALID_INPUT)


class ObjectStorage(ABC):
    """Bounded bytes interface; same-key puts replace, missing deletes succeed.

    No public URLs, ACLs, bucket creation, listing or domain ownership inference.
    Callers must use unique keys when concurrent replacement is undesirable.
    """

    @abstractmethod
    async def put(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> ObjectMetadata: ...

    @abstractmethod
    async def get(self, key: str) -> StoredObject: ...

    @abstractmethod
    async def stat(self, key: str) -> ObjectMetadata: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def check_connection(self) -> None:
        """Probe local I/O or remote bucket access without mutating user objects."""
        ...

    @abstractmethod
    async def close(self) -> None: ...
