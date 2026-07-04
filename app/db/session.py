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
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "language" not in user_columns:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN language VARCHAR(16)"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_light_migrations)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

