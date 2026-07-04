from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Base


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def _run_light_migrations(sync_conn: Connection) -> None:
    """create_all mavjud jadvalga ustun qo'shmaydi, shuning uchun yetishmayotgan
    ustunlarni qo'lda qo'shamiz. Postgres va SQLite uchun mos ishlaydi."""
    inspector = inspect(sync_conn)

    def cols(table: str) -> set[str]:
        return {column["name"] for column in inspector.get_columns(table)}

    def add(table: str, column: str, ddl: str) -> None:
        if column not in cols(table):
            sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))

    add("users", "language", "language VARCHAR(16)")
    add("users", "region_city", "region_city VARCHAR(120)")
    add("users", "region_rayon", "region_rayon VARCHAR(120)")
    add("users", "balance", "balance NUMERIC(14, 2) DEFAULT 0")
    add("doctors", "bonus_balance", "bonus_balance NUMERIC(14, 2) DEFAULT 0")
    add("pharmacies", "inn", "inn VARCHAR(32)")
    add("pharmacies", "filial", "filial VARCHAR(120)")


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_light_migrations)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

