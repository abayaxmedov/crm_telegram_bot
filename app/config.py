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
    # Analitika web-paneli (owner/TOP/product menejer uchun).
    webapp_host: str = "0.0.0.0"
    webapp_port: int = 8080
    webapp_base_url: str = "http://localhost:8080"
    # Kelajakda HTTPS domen olinganda: Telegram ichidagi WebApp tugmasi uchun URL.
    webapp_telegram_url: str | None = None
    # FSM holati saqlanadigan Redis (bot restart/deploy'dan omon qoladi).
    # Bo'sh bo'lsa MemoryStorage ishlatiladi (restart'da holat yo'qoladi).
    redis_url: str | None = None

    # ---- Hisob-faktura (счёт на оплату) rekvizitlari ----
    # Kompaniyaning YAGONA bank hisobi — invoys shapkasiga chiqadi.
    # Bank NOMI ataylab yo'q (foydalanuvchi qarori) — faqat Р/С va МФО.
    invoice_company: str = ""      # Получатель / Поставщик (to'liq yuridik nom)
    invoice_inn: str = ""          # ИНН (СТИР)
    invoice_account: str = ""      # Р/С (H/r — hisob raqami)
    invoice_mfo: str = ""          # МФО
    invoice_address: str = ""      # Адрес (ixtiyoriy — bo'sh bo'lsa qator chiqmaydi)
    invoice_phone: str = ""        # Телефон (ixtiyoriy)
    invoice_oked: str = ""         # ОКЭД (ixtiyoriy)
    invoice_vat_percent: int = 12  # НДС stavkasi (narx НДСsiz kiritiladi, ustiga qo'shiladi)

    def invoice_ready(self) -> bool:
        """Majburiy rekvizitlar to'liq bo'lmasa PDF yasalmaydi (yarim hujjat yuborilmaydi).

        Manzil/telefon/ОКЭД — ixtiyoriy: bo'lmasa o'sha qator tushib qoladi."""
        return all([self.invoice_company, self.invoice_inn, self.invoice_account, self.invoice_mfo])

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
    webapp_host=os.getenv("WEBAPP_HOST", "0.0.0.0").strip(),
    webapp_port=int(os.getenv("WEBAPP_PORT", "8080").strip() or "8080"),
    webapp_base_url=os.getenv("WEBAPP_BASE_URL", "").strip() or f"http://localhost:{os.getenv('WEBAPP_PORT', '8080').strip() or '8080'}",
    webapp_telegram_url=os.getenv("WEBAPP_TELEGRAM_URL", "").strip() or None,
    redis_url=os.getenv("REDIS_URL", "").strip() or None,
    invoice_company=os.getenv("INVOICE_COMPANY", "").strip(),
    invoice_inn=os.getenv("INVOICE_INN", "").strip(),
    invoice_account=os.getenv("INVOICE_ACCOUNT", "").strip(),
    invoice_mfo=os.getenv("INVOICE_MFO", "").strip(),
    invoice_address=os.getenv("INVOICE_ADDRESS", "").strip(),
    invoice_phone=os.getenv("INVOICE_PHONE", "").strip(),
    invoice_oked=os.getenv("INVOICE_OKED", "").strip(),
    invoice_vat_percent=int(os.getenv("INVOICE_VAT_PERCENT", "12").strip() or "12"),
)

