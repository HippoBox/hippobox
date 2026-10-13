"""Application-owned object storage; remote selections share one S3 adapter."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from botocore.exceptions import BotoCoreError
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from hippobox.platform.core.config.settings import Settings
from hippobox.platform.core.object_storage.base import (
    ObjectMetadata,
    ObjectStorage,
    StorageError,
    StorageErrorCode,
    StoredObject,
)
from hippobox.platform.core.object_storage.local import LocalObjectStorage
from hippobox.platform.core.object_storage.s3 import S3ObjectStorage, create_s3_client
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.core.observability.startup_display import shutdown_step, startup_step

__all__ = [
    "ObjectMetadata",
    "ObjectStorage",
    "StorageError",
    "StorageErrorCode",
    "StoredObject",
    "create_object_storage",
    "object_storage_lifespan",
]


logger = get_logger(__name__)


async def create_object_storage(settings: Settings) -> ObjectStorage:
    settings.validate_object_storage()
    if settings.OBJECT_STORAGE_PROVIDER == "local":
        storage = LocalObjectStorage(
            settings.OBJECT_STORAGE_LOCAL_ROOT, settings.OBJECT_STORAGE_MAX_BYTES
        )
        await storage.initialize()
        return storage
    try:
        client = await run_in_threadpool(create_s3_client, settings)
    except (BotoCoreError, OSError):
        raise StorageError(StorageErrorCode.UNAVAILABLE) from None
    return S3ObjectStorage(
        client, settings.OBJECT_STORAGE_S3_BUCKET, settings.OBJECT_STORAGE_MAX_BYTES
    )


@asynccontextmanager
async def object_storage_lifespan(app: FastAPI, settings: Settings) -> AsyncIterator[None]:
    storage: ObjectStorage | None = None
    provider = settings.OBJECT_STORAGE_PROVIDER
    try:
        logger.info("Object storage startup check started (provider=%s).", provider)
        try:
            with startup_step("storage"):
                storage = await create_object_storage(settings)
                await storage.check_connection()
        except (StorageError, ValueError) as exc:
            code = exc.code.value if isinstance(exc, StorageError) else "invalid_configuration"
            logger.error(
                "Object storage startup check failed (provider=%s, code=%s).", provider, code
            )
            raise
        logger.info("Object storage startup check succeeded (provider=%s).", provider)
        app.state.object_storage = storage
        yield
    finally:
        if storage is not None:
            try:
                with shutdown_step("storage"):
                    await storage.close()
            finally:
                if getattr(app.state, "object_storage", None) is storage:
                    del app.state.object_storage
