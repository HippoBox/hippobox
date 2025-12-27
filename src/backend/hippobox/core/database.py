import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from hippobox.core.settings import SETTINGS

log = logging.getLogger("database")


class Base(DeclarativeBase):
    pass


def _create_engine():
    db_url = SETTINGS.DATABASE_URL

    if db_url.startswith("sqlite+aiosqlite"):
        engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
        )
        log.info(f"Using database: {db_url}")
        return engine

    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    log.info(f"Using database: {db_url}")
    return engine


_ENGINE = None
_SESSION_FACTORY = None


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = _create_engine()
    return _ENGINE


def get_session_factory():
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = async_sessionmaker(
            get_engine(),
            autoflush=False,
            expire_on_commit=False,
        )
    return _SESSION_FACTORY


async def init_db():
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database tables created")


async def dispose_db():
    engine = get_engine()
    await engine.dispose()
    log.info("Database engine disposed")


async def _get_session():
    db: AsyncSession = get_session_factory()()
    try:
        yield db
    finally:
        await db.close()


@asynccontextmanager
async def get_db():
    gen = _get_session()
    db = await gen.__anext__()
    try:
        yield db
    finally:
        try:
            await gen.aclose()
        except StopAsyncIteration:
            pass
