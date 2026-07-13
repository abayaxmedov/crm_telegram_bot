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
    add("users", "region_id", "region_id INTEGER")
    add("users", "balance", "balance NUMERIC(14, 2) DEFAULT 0")
    add("users", "ball_balance", "ball_balance INTEGER DEFAULT 0")
    add("doctors", "bonus_balance", "bonus_balance NUMERIC(14, 2) DEFAULT 0")
    add("doctors", "region_id", "region_id INTEGER")
    add("doctors", "approval_status", "approval_status VARCHAR(20) DEFAULT 'approved'")
    add("doctors", "created_by_id", "created_by_id INTEGER")
    add("doctors", "ball_balance", "ball_balance INTEGER DEFAULT 0")
    add("doctors", "user_id", "user_id INTEGER")
    add("doctors", "lpu_id", "lpu_id INTEGER")
    add("pharmacies", "inn", "inn VARCHAR(32)")
    add("pharmacies", "filial", "filial VARCHAR(120)")
    add("pharmacies", "region_id", "region_id INTEGER")
    add("pharmacies", "approval_status", "approval_status VARCHAR(20) DEFAULT 'approved'")
    add("drugs", "price", "price NUMERIC(14, 2) DEFAULT 0")
    add("drugs", "ball", "ball INTEGER DEFAULT 0")
    add("sale_items", "price", "price NUMERIC(14, 2) DEFAULT 0")
    add("sale_items", "ball", "ball INTEGER DEFAULT 0")
    add("sales", "total_price", "total_price NUMERIC(14, 2) DEFAULT 0")
    add("sales", "total_ball", "total_ball INTEGER DEFAULT 0")
    add("contracts", "file_id", "file_id VARCHAR(255)")
    add("daily_reports", "doctor_id", "doctor_id INTEGER")
    add("daily_reports", "pharmacy_id", "pharmacy_id INTEGER")
    add("daily_reports", "latitude", "latitude NUMERIC(10, 7)")
    add("daily_reports", "longitude", "longitude NUMERIC(10, 7)")

    # Enum ustunlari string sifatida saqlanadi (native_enum=False). Yangi enum
    # qiymatlari (masalan "regional_manager" = 16 belgi) eski, tor VARCHAR ustunlarga
    # sig'masligi mumkin — create_all mavjud ustun tipini o'zgartirmaydi. Postgres'da
    # kengaytiramiz (SQLite VARCHAR uzunligini majburlamaydi, shuning uchun skip).
    if sync_conn.dialect.name == "postgresql":
        for table, column in (
            ("users", "role"),
            ("doctors", "approval_status"),
            ("pharmacies", "approval_status"),
            ("ball_transactions", "kind"),
            ("ball_transactions", "status"),
        ):
            if column in cols(table):
                sync_conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR(32)"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_light_migrations)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

