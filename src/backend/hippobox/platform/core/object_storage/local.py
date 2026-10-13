"""Private local records: metadata and payload replaced together atomically."""

import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO, TypeVar

from starlette.concurrency import run_in_threadpool

from hippobox.platform.core.object_storage.base import (
    ObjectMetadata,
    ObjectStorage,
    StorageError,
    StorageErrorCode,
    StoredObject,
    validate_content_type,
    validate_key,
)

T = TypeVar("T")


class LocalObjectStorage(ObjectStorage):
    def __init__(self, root: Path, max_bytes: int):
        # Root and its parents are operator-owned, never user-writable paths.
        self.root = root.resolve()
        self.max_bytes = max_bytes
        self._closed = False

    async def initialize(self) -> None:
        await self._run(self._initialize)

    def _initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    async def check_connection(self) -> None:
        await self._run(self._check_connection)

    def _check_connection(self) -> None:
        # A unique private probe must complete write/read/delete before startup succeeds.
        fd, name = tempfile.mkstemp(prefix=".probe-", dir=self.root)
        try:
            with os.fdopen(fd, "w+b") as stream:
                expected = b"b4fastapi-storage-probe"
                stream.write(expected)
                stream.flush()
                os.fsync(stream.fileno())
                stream.seek(0)
                if stream.read() != expected:
                    raise StorageError(StorageErrorCode.CORRUPT_OBJECT)
        finally:
            os.unlink(name)

    def _path(self, key: str) -> Path:
        validate_key(key)
        return self.root / (hashlib.sha256(key.encode()).hexdigest() + ".object")

    async def _run(self, operation: Callable[[], T]) -> T:
        if self._closed:
            raise StorageError(StorageErrorCode.CLOSED)
        try:
            return await run_in_threadpool(operation)
        except FileNotFoundError:
            raise StorageError(StorageErrorCode.NOT_FOUND) from None
        except PermissionError:
            raise StorageError(StorageErrorCode.ACCESS_DENIED) from None
        except OSError:
            raise StorageError(StorageErrorCode.UNAVAILABLE) from None

    async def put(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> ObjectMetadata:
        path = self._path(key)
        validate_content_type(content_type)
        if len(data) > self.max_bytes:
            raise StorageError(StorageErrorCode.TOO_LARGE)
        metadata = ObjectMetadata(key, len(data), content_type)

        def write() -> ObjectMetadata:
            header = json.dumps(
                {"version": 1, "key": key, "size": len(data), "content_type": content_type}
            ).encode()
            fd, name = tempfile.mkstemp(prefix=".put-", dir=self.root)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(len(header).to_bytes(4, "big"))
                    stream.write(header)
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, path)
            finally:
                Path(name).unlink(missing_ok=True)
            return metadata

        return await self._run(write)

    def _read(self, key: str, include_data: bool) -> StoredObject:
        # Hash-only flat filenames prevent parent traversal; no-follow rejects object symlinks.
        fd = os.open(self._path(key), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise StorageError(StorageErrorCode.CORRUPT_OBJECT)
            metadata = self._read_header(stream, key, info.st_size)
            if include_data and metadata.size > self.max_bytes:
                raise StorageError(StorageErrorCode.TOO_LARGE)
            data = stream.read(metadata.size + 1) if include_data else b""
            if include_data and len(data) != metadata.size:
                raise StorageError(StorageErrorCode.CORRUPT_OBJECT)
            return StoredObject(metadata, data)

    @staticmethod
    def _read_header(stream: BinaryIO, key: str, file_size: int) -> ObjectMetadata:
        try:
            size_bytes = stream.read(4)
            length = int.from_bytes(size_bytes, "big")
            if len(size_bytes) != 4 or not 0 < length <= 4096:
                raise ValueError
            header = json.loads(stream.read(length))
            if (
                header["version"] != 1
                or header["key"] != key
                or type(header["size"]) is not int
                or header["size"] < 0
                or header["size"] != file_size - 4 - length
            ):
                raise ValueError
            validate_content_type(header["content_type"])
            return ObjectMetadata(key, header["size"], header["content_type"])
        except (ValueError, KeyError, TypeError, StorageError):
            raise StorageError(StorageErrorCode.CORRUPT_OBJECT) from None

    async def get(self, key: str) -> StoredObject:
        validate_key(key)
        return await self._run(lambda: self._read(key, True))

    async def stat(self, key: str) -> ObjectMetadata:
        validate_key(key)
        return (await self._run(lambda: self._read(key, False))).metadata

    async def delete(self, key: str) -> None:
        path = self._path(key)
        await self._run(lambda: path.unlink(missing_ok=True))

    async def close(self) -> None:
        self._closed = True
