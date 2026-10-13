"""HippoBox owns schema evolution; upstream migration history is reference-only."""
async def run_startup_schema_migrations(database_url: str) -> None:
    raise RuntimeError("Use hippobox.server:app; upstream Alembic history does not apply to HippoBox")
