"""One S3 transport for AWS S3, Cloudflare R2 and Supabase S3 endpoints."""

from collections.abc import Callable
from typing import TypeVar

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from starlette.concurrency import run_in_threadpool

from hippobox.platform.core.config.settings import Settings
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


def create_s3_client(settings: Settings) -> BaseClient:
    """Credential chain is used for AWS when explicit keys are absent."""
    provider = settings.OBJECT_STORAGE_PROVIDER
    region = "auto" if provider == "r2" else settings.OBJECT_STORAGE_S3_REGION
    style = settings.OBJECT_STORAGE_S3_ADDRESSING_STYLE
    if style == "auto" and provider in ("r2", "supabase"):
        style = "path"
    credentials = {}
    if settings.OBJECT_STORAGE_S3_ACCESS_KEY_ID:
        credentials = {
            "aws_access_key_id": settings.OBJECT_STORAGE_S3_ACCESS_KEY_ID.get_secret_value(),
            "aws_secret_access_key": settings.OBJECT_STORAGE_S3_SECRET_ACCESS_KEY.get_secret_value(),
        }
        if settings.OBJECT_STORAGE_S3_SESSION_TOKEN:
            credentials["aws_session_token"] = (
                settings.OBJECT_STORAGE_S3_SESSION_TOKEN.get_secret_value()
            )
    return boto3.session.Session().client(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_S3_ENDPOINT_URL or None,
        region_name=region or None,
        config=Config(
            signature_version="s3v4",
            connect_timeout=settings.OBJECT_STORAGE_TIMEOUT_SECONDS,
            read_timeout=settings.OBJECT_STORAGE_TIMEOUT_SECONDS,
            retries={"mode": "standard", "total_max_attempts": 3},
            s3={"addressing_style": style},
            # Optional AWS checksum trailers are not portable to every S3 service.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
        **credentials,
    )


class S3ObjectStorage(ObjectStorage):
    def __init__(self, client: BaseClient, bucket: str, max_bytes: int):
        self._client = client
        self.bucket = bucket
        self.max_bytes = max_bytes
        self._closed = False

    async def _run(self, operation: Callable[[], T], *, deleting: bool = False) -> T:
        if self._closed:
            raise StorageError(StorageErrorCode.CLOSED)
        try:
            return await run_in_threadpool(operation)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            # Do not treat NoSuchBucket as a missing object or a successful deletion.
            if code in {"NoSuchKey", "NotFound", "404"}:
                if deleting:
                    return None
                mapped = StorageErrorCode.NOT_FOUND
            elif code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch", "403"}:
                mapped = StorageErrorCode.ACCESS_DENIED
            else:
                mapped = StorageErrorCode.UNAVAILABLE
            raise StorageError(mapped) from None
        except (BotoCoreError, OSError):
            raise StorageError(StorageErrorCode.UNAVAILABLE) from None

    async def put(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> ObjectMetadata:
        validate_key(key)
        validate_content_type(content_type)
        if len(data) > self.max_bytes:
            raise StorageError(StorageErrorCode.TOO_LARGE)
        await self._run(
            lambda: self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        )
        return ObjectMetadata(key, len(data), content_type)

    async def get(self, key: str) -> StoredObject:
        validate_key(key)

        def read() -> StoredObject:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            try:
                size = response["ContentLength"]
                if size > self.max_bytes:
                    raise StorageError(StorageErrorCode.TOO_LARGE)
                data = body.read(self.max_bytes + 1)
                if len(data) > self.max_bytes:
                    raise StorageError(StorageErrorCode.TOO_LARGE)
                if len(data) != size:
                    raise StorageError(StorageErrorCode.CORRUPT_OBJECT)
                return StoredObject(
                    ObjectMetadata(
                        key, size, response.get("ContentType", "application/octet-stream")
                    ),
                    data,
                )
            finally:
                body.close()

        return await self._run(read)

    async def stat(self, key: str) -> ObjectMetadata:
        validate_key(key)
        response = await self._run(lambda: self._client.head_object(Bucket=self.bucket, Key=key))
        return ObjectMetadata(
            key, response["ContentLength"], response.get("ContentType", "application/octet-stream")
        )

    async def delete(self, key: str) -> None:
        validate_key(key)
        await self._run(
            lambda: self._client.delete_object(Bucket=self.bucket, Key=key), deleting=True
        )

    async def check_connection(self) -> None:
        # Read-only bucket check: object put/delete permissions are a separate rollout check.
        await self._run(lambda: self._client.head_bucket(Bucket=self.bucket))

    async def close(self) -> None:
        if not self._closed:
            await run_in_threadpool(self._client.close)
            self._closed = True
