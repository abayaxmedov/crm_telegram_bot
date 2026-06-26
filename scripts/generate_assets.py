from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent.parent
PHOTO_DIR = BASE_DIR / "assets" / "photos"
STICKER_DIR = BASE_DIR / "assets" / "stickers"


PHOTO_SPECS = {
    "welcome.jpg": ("Yopiq CRM Bot", "Vrachlar • Aptekalar • Hisobotlar", (29, 72, 99), (240, 183, 77)),
    "menu.jpg": ("Asosiy menyu", "Role bo'yicha aniq va tartibli ish", (42, 84, 69), (233, 116, 81)),
    "admin.jpg": ("Admin Panel", "Invite token • Rollar • Nazorat", (73, 57, 120), (85, 169, 153)),
    "doctors.jpg": ("Vrachlar", "Kontakt, lokatsiya va kategoriya", (20, 105, 126), (244, 162, 97)),
    "pharmacies.jpg": ("Aptekalar", "Mas'ul shaxs va filial ma'lumotlari", (91, 109, 53), (231, 111, 81)),
    "daily.jpg": ("Kundalik", "Yozma va voice hisobotlar", (39, 76, 119), (232, 184, 109)),
    "requests.jpg": ("Zayavkalar", "Yangi • Jarayonda • Bajarildi", (107, 68, 35), (90, 143, 123)),
    "finance.jpg": ("Finans", "Kirim, chiqim va qarzdorlik", (33, 92, 84), (238, 137, 91)),
    "salary.jpg": ("Moy zarplata", "Oylik • Bonus • Jarima • Jami", (95, 64, 101), (110, 178, 154)),
}

STICKER_SPECS = {
    "welcome.webp": ("CRM", "XUSH KELDINGIZ", (25, 86, 104), (243, 188, 77)),
    "admin.webp": ("OWNER", "NAZORAT", (89, 66, 135), (97, 190, 170)),
    "daily.webp": ("REPORT", "SAQLANDI", (37, 91, 142), (241, 170, 94)),
    "done.webp": ("OK", "TAYYOR", (43, 132, 98), (238, 112, 88)),
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def make_gradient(size: tuple[int, int], start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            ratio = (x / width * 0.65) + (y / height * 0.35)
            pixels[x, y] = tuple(int(start[i] * (1 - ratio) + end[i] * ratio) for i in range(3))
    return image


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int = 10,
) -> None:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    x, y = position
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += draw.textbbox((0, 0), line, font=font)[3] + line_gap


def create_photo(filename: str, title: str, subtitle: str, start: tuple[int, int, int], end: tuple[int, int, int]) -> None:
    image = make_gradient((1280, 720), start, end)
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = load_font(76, bold=True)
    subtitle_font = load_font(34)
    small_font = load_font(24)

    for idx in range(8):
        x = 780 + idx * 55
        y = 90 + int(math.sin(idx) * 35)
        draw.rounded_rectangle((x, y, x + 260, y + 95), radius=28, fill=(255, 255, 255, 30), outline=(255, 255, 255, 65))

    draw.rounded_rectangle((70, 88, 750, 610), radius=42, fill=(255, 255, 255, 34), outline=(255, 255, 255, 80), width=2)
    draw.ellipse((900, 380, 1210, 690), fill=(255, 255, 255, 32))
    draw.ellipse((1015, 70, 1190, 245), fill=(0, 0, 0, 28))

    draw.text((115, 155), title, font=title_font, fill=(255, 255, 255, 255))
    draw_wrapped_text(draw, (120, 285), subtitle, subtitle_font, (255, 248, 226, 245), 560)
    draw.text((122, 505), "Telegram ichida tezkor boshqaruv", font=small_font, fill=(255, 255, 255, 210))

    image.save(PHOTO_DIR / filename, quality=92, optimize=True)


def create_sticker(filename: str, title: str, subtitle: str, start: tuple[int, int, int], end: tuple[int, int, int]) -> None:
    base = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    grad = make_gradient((512, 512), start, end).convert("RGBA")
    mask = Image.new("L", (512, 512), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((38, 48, 474, 464), radius=116, fill=255)
    base.alpha_composite(grad, (0, 0))
    base.putalpha(mask)

    draw = ImageDraw.Draw(base, "RGBA")
    draw.rounded_rectangle((62, 72, 450, 440), radius=92, outline=(255, 255, 255, 92), width=5)
    draw.ellipse((348, 72, 438, 162), fill=(255, 255, 255, 42))
    draw.ellipse((82, 342, 180, 440), fill=(0, 0, 0, 32))

    title_font = load_font(88, bold=True)
    subtitle_font = load_font(34, bold=True)
    title_box = draw.textbbox((0, 0), title, font=title_font)
    subtitle_box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((512 - (title_box[2] - title_box[0])) / 2, 175), title, font=title_font, fill=(255, 255, 255, 255))
    draw.text(
        ((512 - (subtitle_box[2] - subtitle_box[0])) / 2, 285),
        subtitle,
        font=subtitle_font,
        fill=(255, 248, 225, 245),
    )
    base.save(STICKER_DIR / filename, "WEBP", quality=92, method=6)


def main() -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    STICKER_DIR.mkdir(parents=True, exist_ok=True)

    for filename, spec in PHOTO_SPECS.items():
        create_photo(filename, *spec)
    for filename, spec in STICKER_SPECS.items():
        create_sticker(filename, *spec)


if __name__ == "__main__":
    main()

