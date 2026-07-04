from __future__ import annotations

"""CRM bot uchun media (rasm va stiker) generatori.

Zamonaviy, to'q korporativ uslub: to'q navy fon, yumaloq oq "карточка",
акцент рангли иконка бейджи, тоза типографика. Ҳар бир тил (uz_cyrl, ru)
учун алоҳида тўплам ясайди:
    assets/photos/<lang>/<screen>.jpg
    assets/stickers/<lang>/<name>.webp
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


BASE_DIR = Path(__file__).resolve().parent.parent
PHOTO_ROOT = BASE_DIR / "assets" / "photos"
STICKER_ROOT = BASE_DIR / "assets" / "stickers"

SS = 2  # supersampling (silliq qirralar uchun)

UZ = "uz_cyrl"
RU = "ru"
LANGS = (UZ, RU)

# --- Ranglar palitrasi --------------------------------------------------------

BG_TOP = (15, 25, 43)          # to'q navy
BG_BOTTOM = (8, 12, 22)        # deyarli qora navy
CARD_FILL = (250, 251, 253, 255)   # oq kartochka
CARD_BORDER = (255, 255, 255, 60)
WHITE = (255, 255, 255, 255)
INK = (24, 36, 60, 255)            # to'q navy matn (kartochkada)
INK_SUB = (92, 107, 133, 255)      # slate subtitle
INK_FOOT = (144, 158, 180, 255)    # och footer
MUTED = (188, 202, 222, 255)       # to'q fon ustidagi och matn
GRID = (255, 255, 255, 10)

ACCENTS = {
    "welcome": (79, 142, 255),
    "menu": (110, 140, 255),
    "admin": (156, 126, 255),
    "doctors": (52, 197, 216),
    "pharmacies": (80, 208, 138),
    "daily": (243, 179, 77),
    "requests": (243, 137, 77),
    "finance": (52, 197, 138),
    "salary": (226, 110, 158),
    "done": (70, 208, 138),
}

COMPANY = "Ichki CRM"

# --- Matnlar (til bo'yicha) ---------------------------------------------------

PHOTO_TEXT = {
    "welcome": {
        UZ: ("Ёпиқ CRM бот", "Врачлар • Аптекалар • Ҳисоботлар"),
        RU: ("Закрытый CRM-бот", "Врачи • Аптеки • Отчёты"),
    },
    "menu": {
        UZ: ("Асосий меню", "Роль бўйича аниқ ва тартибли иш"),
        RU: ("Главное меню", "Чёткая работа по ролям"),
    },
    "admin": {
        UZ: ("Админ панель", "Invite токен • Роллар • Назорат"),
        RU: ("Админ-панель", "Invite-токен • Роли • Контроль"),
    },
    "doctors": {
        UZ: ("Врачлар", "Контакт, локация ва категория"),
        RU: ("Врачи", "Контакт, локация и категория"),
    },
    "pharmacies": {
        UZ: ("Аптекалар", "Масъул шахс ва филиал маълумоти"),
        RU: ("Аптеки", "Ответственное лицо и филиал"),
    },
    "daily": {
        UZ: ("Кундалик ҳисобот", "Ёзма ва овозли ҳисоботлар"),
        RU: ("Ежедневный отчёт", "Текстовые и голосовые отчёты"),
    },
    "requests": {
        UZ: ("Заявкалар", "Янги • Жараёнда • Бажарилди"),
        RU: ("Заявки", "Новая • В процессе • Выполнено"),
    },
    "finance": {
        UZ: ("Молия", "Кирим, чиқим ва қарздорлик"),
        RU: ("Финансы", "Приход, расход и задолженность"),
    },
    "salary": {
        UZ: ("Ойлик", "Ойлик • Бонус • Жарима • Жами"),
        RU: ("Зарплата", "Оклад • Бонус • Штраф • Итого"),
    },
}

STICKER_TEXT = {
    "welcome": {"title": "CRM", UZ: "ХУШ КЕЛДИНГИЗ", RU: "ДОБРО ПОЖАЛОВАТЬ"},
    "admin": {"title": "OWNER", UZ: "НАЗОРАТ", RU: "КОНТРОЛЬ"},
    "daily": {"title": "REPORT", UZ: "САҚЛАНДИ", RU: "СОХРАНЕНО"},
    "done": {"title": "OK", UZ: "ТАЙЁР", RU: "ГОТОВО"},
}

# rasm ekrani -> ikonka turi
PHOTO_ICON = {
    "welcome": "spark",
    "menu": "grid",
    "admin": "shield",
    "doctors": "cross",
    "pharmacies": "pill",
    "daily": "clipboard",
    "requests": "box",
    "finance": "bars",
    "salary": "wallet",
}
STICKER_ICON = {"welcome": "spark", "admin": "shield", "daily": "clipboard", "done": "check"}


# --- Shrift -------------------------------------------------------------------

def _font(size: int, bold: bool = False):
    # Kirill (ў, қ, ғ, ҳ) va rus harflarini to'liq qoplaydigan shriftlar.
    candidates = []
    if bold:
        candidates += [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    candidates += [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _fit_font(draw, text, max_width, start_size, bold=True):
    size = start_size
    while size > 22:
        font = _font(size, bold=bold)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 2
    return _font(size, bold=bold)


# --- Fon elementlari ----------------------------------------------------------

def _vgradient(size, top, bottom):
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        r = y / max(h - 1, 1)
        grad.putpixel((0, y), tuple(int(top[i] * (1 - r) + bottom[i] * r) for i in range(3)))
    return grad.resize((w, h))


def _glow(size, center, radius, color, alpha):
    """Yumshoq акцент нур. Тезлик учун кичик масштабда чизилиб, кейин катталаштирилади."""
    q = 6  # масштаб коэффициенти
    w, h = size[0] // q, size[1] // q
    cx, cy = center[0] // q, center[1] // q
    r = max(2, radius // q)
    small = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(small).ellipse((cx - r, cy - r, cx + r, cy + r), fill=color + (alpha,))
    small = small.filter(ImageFilter.GaussianBlur(max(1, r // 2)))
    return small.resize(size, Image.BILINEAR)


def _dot_grid(size, step, color):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = size
    r = max(2, step // 22)
    for x in range(step, w, step):
        for y in range(step, h, step):
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    return layer


# --- Ikonkalar (oq chiziqли gliflar) -----------------------------------------

def _tline(draw, pts, color, w):
    draw.line(pts, fill=color, width=w, joint="curve")
    r = w // 2
    for x, y in (pts[0], pts[-1]):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def draw_icon(draw, kind, cx, cy, s, color=WHITE):
    """(cx,cy) markazда, ярим ўлчам s бўлган иконка."""
    w = max(6, s // 6)

    if kind == "spark":
        pts = [(cx, cy - s), (cx + s * 0.28, cy - s * 0.28), (cx + s, cy),
               (cx + s * 0.28, cy + s * 0.28), (cx, cy + s), (cx - s * 0.28, cy + s * 0.28),
               (cx - s, cy), (cx - s * 0.28, cy - s * 0.28)]
        draw.polygon(pts, fill=color)
    elif kind == "grid":
        cell = int(s * 0.72)
        rad = max(6, cell // 4)
        gap = int(s * 0.18)
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            x0 = cx + (gap if dx > 0 else -cell - gap)
            y0 = cy + (gap if dy > 0 else -cell - gap)
            draw.rounded_rectangle((x0, y0, x0 + cell, y0 + cell), radius=rad, fill=color)
    elif kind == "shield":
        top = cy - s
        pts = [(cx, top), (cx + s * 0.82, cy - s * 0.45), (cx + s * 0.82, cy + s * 0.2),
               (cx, cy + s), (cx - s * 0.82, cy + s * 0.2), (cx - s * 0.82, cy - s * 0.45)]
        draw.polygon(pts, outline=color, width=w)
        _tline(draw, [(cx - s * 0.34, cy), (cx - s * 0.05, cy + s * 0.32), (cx + s * 0.42, cy - s * 0.28)], color, w)
    elif kind == "cross":
        t = int(s * 0.34)
        draw.rounded_rectangle((cx - t, cy - s, cx + t, cy + s), radius=t, fill=color)
        draw.rounded_rectangle((cx - s, cy - t, cx + s, cy + t), radius=t, fill=color)
    elif kind == "pill":
        # gorizontal kapsula + ajratuvchi chiziq
        draw.rounded_rectangle((cx - s, cy - s * 0.52, cx + s, cy + s * 0.52), radius=int(s * 0.52),
                               outline=color, width=w)
        _tline(draw, [(cx, cy - s * 0.5), (cx, cy + s * 0.5)], color, max(4, w - 2))
    elif kind == "clipboard":
        draw.rounded_rectangle((cx - s * 0.72, cy - s, cx + s * 0.72, cy + s), radius=int(s * 0.2),
                               outline=color, width=w)
        clip_w = int(s * 0.5)
        draw.rounded_rectangle((cx - clip_w, cy - s - w, cx + clip_w, cy - s * 0.62), radius=max(6, w),
                               fill=color)
        for i, yy in enumerate((-0.24, 0.1, 0.44)):
            ln = 0.48 if i < 2 else 0.3
            _tline(draw, [(cx - s * 0.44, cy + s * yy), (cx + s * ln, cy + s * yy)], color, max(4, w - 2))
    elif kind == "box":
        draw.rounded_rectangle((cx - s * 0.82, cy - s * 0.72, cx + s * 0.82, cy + s * 0.82),
                               radius=int(s * 0.16), outline=color, width=w)
        _tline(draw, [(cx - s * 0.82, cy - s * 0.05), (cx + s * 0.82, cy - s * 0.05)], color, w)
        _tline(draw, [(cx, cy - s * 0.72), (cx, cy - s * 0.05)], color, w)
    elif kind == "bars":
        base = cy + s * 0.82
        bw = int(s * 0.42)
        heights = (0.7, 1.15, 1.6)
        xs = (cx - s * 0.9, cx - bw * 0.5, cx + s * 0.9 - bw)
        for x, hf in zip(xs, heights):
            draw.rounded_rectangle((x, base - s * hf, x + bw, base), radius=max(5, bw // 4), fill=color)
    elif kind == "wallet":
        draw.rounded_rectangle((cx - s, cy - s * 0.66, cx + s, cy + s * 0.66), radius=int(s * 0.26),
                               outline=color, width=w)
        draw.rounded_rectangle((cx + s * 0.2, cy - s * 0.12, cx + s + w, cy + s * 0.2), radius=max(6, w),
                               fill=color)
    elif kind == "check":
        _tline(draw, [(cx - s * 0.6, cy + s * 0.05), (cx - s * 0.12, cy + s * 0.52), (cx + s * 0.66, cy - s * 0.5)],
               color, int(w * 1.3))


def _round_shadow(size, box, radius, alpha, offset=0):
    q = 4
    w, h = size[0] // q, size[1] // q
    small = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bx = (box[0] // q, box[1] // q + offset // q, box[2] // q, box[3] // q + offset // q)
    ImageDraw.Draw(small).rounded_rectangle(bx, radius=radius // q, fill=(0, 0, 0, alpha))
    small = small.filter(ImageFilter.GaussianBlur(6))
    return small.resize(size, Image.BILINEAR)


def _badge(base, x, y, size, accent, icon, glow=True):
    """Акцент рангли иконка бейджи."""
    if glow:
        base.alpha_composite(_glow(base.size, (x + size // 2, y + size // 2), int(size * 0.9), accent, 120))
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((x, y, x + size, y + size), radius=int(size * 0.28), fill=accent + (255,))
    draw_icon(d, icon, x + size // 2, y + size // 2, int(size * 0.3))


# --- Rasm (photo) -------------------------------------------------------------

def create_photo(path, screen, lang):
    W, H = 1280 * SS, 720 * SS
    accent = ACCENTS[screen]
    title, subtitle = PHOTO_TEXT[screen][lang]

    img = _vgradient((W, H), BG_TOP, BG_BOTTOM).convert("RGBA")
    img.alpha_composite(_dot_grid((W, H), 46 * SS, GRID))
    img.alpha_composite(_glow((W, H), (W - 250 * SS, 170 * SS), 360 * SS, accent, 70))
    img.alpha_composite(_glow((W, H), (150 * SS, H - 60 * SS), 260 * SS, accent, 30))

    d = ImageDraw.Draw(img, "RGBA")

    # dekоратив halqalar (o'ng tomonda)
    for rr in (150, 224, 298):
        d.ellipse((W - 240 * SS - rr * SS, 175 * SS - rr * SS, W - 240 * SS + rr * SS, 175 * SS + rr * SS),
                  outline=(255, 255, 255, 14), width=max(2, SS))

    # Карточка koordinatalari
    cx0, cy0, cx1, cy1 = 74 * SS, 120 * SS, 800 * SS, 600 * SS
    rad = 40 * SS

    # Kartochka soyasi (chuqurlik uchun)
    img.alpha_composite(_round_shadow((W, H), (cx0, cy0, cx1, cy1), rad, alpha=120, offset=18 * SS))

    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((cx0, cy0, cx1, cy1), radius=rad, fill=CARD_FILL, outline=CARD_BORDER, width=max(2, SS))
    # chap akcent chiziq
    d.rounded_rectangle((cx0 + 0, cy0 + 34 * SS, cx0 + 9 * SS, cy1 - 34 * SS), radius=4 * SS, fill=accent + (255,))

    pad = cx0 + 56 * SS

    # Иконка бейджи (glow yo'q — oq kartochkada toza turadi)
    _badge(img, pad, cy0 + 44 * SS, 128 * SS, accent, PHOTO_ICON[screen], glow=False)
    d = ImageDraw.Draw(img, "RGBA")

    # top-right монограма (акцент рамка + акцент матн)
    mb = 64 * SS
    mx, my = cx1 - mb - 34 * SS, cy0 + 34 * SS
    d.rounded_rectangle((mx, my, mx + mb, my + mb), radius=18 * SS, outline=accent + (255,), width=max(3, 2 * SS))
    d.text((mx + mb / 2, my + mb / 2 + SS), "CRM", font=_font(24 * SS, bold=True), fill=accent + (255,), anchor="mm")

    # Sarlavha
    title_font = _fit_font(d, title, 600 * SS, 62 * SS, bold=True)
    d.text((pad, cy0 + 214 * SS), title, font=title_font, fill=INK)

    # Акцент ажратгич
    d.rounded_rectangle((pad, cy0 + 300 * SS, pad + 66 * SS, cy0 + 307 * SS), radius=3 * SS, fill=accent + (255,))

    # Subtitle (o'ralgan)
    sub_font = _font(30 * SS)
    _wrapped(d, (pad, cy0 + 330 * SS), subtitle, sub_font, INK_SUB, 600 * SS, 12 * SS)

    # Footer
    fy = cy1 - 62 * SS
    d.ellipse((pad, fy + 5 * SS, pad + 15 * SS, fy + 20 * SS), fill=accent + (255,))
    d.text((pad + 28 * SS, fy + 1 * SS), f"{COMPANY}   ·   Telegram CRM", font=_font(24 * SS, bold=True), fill=INK_FOOT)

    out = img.convert("RGB").resize((1280, 720), Image.LANCZOS)
    out.save(path, quality=92, optimize=True)


def _wrapped(draw, pos, text, font, fill, max_width, line_gap):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    x, y = pos
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap


# --- Stiker -------------------------------------------------------------------

def create_sticker(path, name, lang):
    S = 512 * SS
    accent = ACCENTS.get(name, ACCENTS["done"])
    spec = STICKER_TEXT[name]

    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    grad = _vgradient((S, S), BG_TOP, BG_BOTTOM).convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((30 * SS, 30 * SS, S - 30 * SS, S - 30 * SS), radius=120 * SS, fill=255)
    base.paste(grad, (0, 0), mask)

    base.alpha_composite(_glow((S, S), (S // 2, 150 * SS), 220 * SS, accent, 90))

    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((56 * SS, 56 * SS, S - 56 * SS, S - 56 * SS), radius=96 * SS,
                        outline=accent + (150,), width=6 * SS)

    _badge(base, S // 2 - 74 * SS, 96 * SS, 148 * SS, accent, STICKER_ICON[name])
    d = ImageDraw.Draw(base, "RGBA")

    tf = _font(46 * SS, bold=True)
    d.text((S // 2, 300 * SS), spec["title"], font=tf, fill=WHITE, anchor="mm")

    status = spec[lang]
    sf = _fit_font(d, status, S - 150 * SS, 34 * SS, bold=True)
    d.text((S // 2, 372 * SS), status, font=sf, fill=accent + (255,), anchor="mm")

    out = base.resize((512, 512), Image.LANCZOS)
    out.save(path, "WEBP", quality=92, method=3)


# --- Main ---------------------------------------------------------------------

def main() -> None:
    for lang in LANGS:
        photo_dir = PHOTO_ROOT / lang
        sticker_dir = STICKER_ROOT / lang
        photo_dir.mkdir(parents=True, exist_ok=True)
        sticker_dir.mkdir(parents=True, exist_ok=True)

        for screen in PHOTO_TEXT:
            create_photo(photo_dir / f"{screen}.jpg", screen, lang)
        for name in STICKER_TEXT:
            create_sticker(sticker_dir / f"{name}.webp", name, lang)

    print("Generated photos & stickers for:", ", ".join(LANGS))


if __name__ == "__main__":
    main()
