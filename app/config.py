from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = BASE_DIR / ".env") -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def parse_int_tuple(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()

    items: list[int] = []
    for chunk in value.replace(";", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            items.append(int(chunk))
    return tuple(items)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    owner_ids: tuple[int, ...]
    assets_dir: Path
    company_name: str
    default_timezone: str
    bot_username: str | None = None

    def validate(self) -> None:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN .env faylida yoki environment ichida berilishi kerak.")
        if not self.owner_ids:
            raise RuntimeError("OWNER_IDS kamida bitta Telegram ID bo'lishi kerak.")


load_dotenv()

settings = Settings(
    bot_token=os.getenv("BOT_TOKEN", "").strip(),
    database_url=os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://crm_bot:crm_bot@localhost:5432/crm_bot",
    ).strip(),
    owner_ids=parse_int_tuple(os.getenv("OWNER_IDS")) or (89245245, 6087841574),
    assets_dir=Path(os.getenv("ASSETS_DIR", BASE_DIR / "assets")).resolve(),
    company_name=os.getenv("COMPANY_NAME", "Ichki CRM").strip(),
    default_timezone=os.getenv("TZ", "Asia/Tashkent").strip(),
    bot_username=os.getenv("BOT_USERNAME", "").strip() or None,
)

