from __future__ import annotations

"""Ҳисоб-фактура (счёт на оплату) — zayavka uchun PDF.

Format mijoz bergan namunadan (Invoice_3.pdf) olingan: shapkada kompaniyaning
bank rekvizitlari, so'ng Поставщик/Покупатель/Основание, tovarlar jadvali va
imzo satrlari.

MUHIM — НДС: dori narxi bazaga **НДССИЗ** kiritiladi, invoysda ustiga qo'shiladi:
    Цена с НДС    = narx × 1.12
    Сумма без НДС = narx × soni
    НДС (12%)     = Сумма без НДС × 0.12
    Сумма с НДС   = Сумма без НДС + НДС
Ya'ni dorixona to'laydigan summa — owner kiritgan narxdan 12% ko'p.

50% to'lov shartida invoys TO'LIQ summaga yoziladi (tovar to'liq jo'natiladi),
ostiga "К оплате (50% предоплата)" va "Остаток" satrlari qo'shiladi.
"""

from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import settings

# Kirill + lotin ikkalasi kerak ("АНДИЖОН" va "MAS'ULIYATI CHEKLANGAN" bir hujjatda).
# reportlab ichki shriftlarida kirill yo'q — DejaVu ishlatamiz (Docker'da o'rnatiladi).
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/DejaVuSans.ttf",  # lokal test (macOS)
    "/Library/Fonts/DejaVuSans.ttf",
]

FONT = "InvoiceFont"
FONT_BOLD = "InvoiceFont-Bold"
_registered = False


def _register_fonts() -> bool:
    """Shriftlarni ro'yxatdan o'tkazadi. Topilmasa False (PDF yasalmaydi)."""
    global _registered
    if _registered:
        return True
    regular = next((p for p in _FONT_CANDIDATES if p.endswith("DejaVuSans.ttf") and Path(p).exists()), None)
    if regular is None:
        return False
    bold = next(
        (p for p in _FONT_CANDIDATES if p.endswith("DejaVuSans-Bold.ttf") and Path(p).exists()),
        regular,  # bold topilmasa oddiysi bilan ishlaydi (hujjat baribir chiqadi)
    )
    pdfmetrics.registerFont(TTFont(FONT, regular))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, bold))
    _registered = True
    return True


def _money(value: Decimal) -> str:
    """1234567.891 -> '1234567.89' (namunadagi kabi ajratkichsiz)."""
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def invoice_amounts(request) -> dict:
    """Zayavka bo'yicha summalar (items EAGER-LOAD bo'lishi shart).

    Qaytadi: net (НДСсиз), vat, gross (НДС bilan), prepay, remainder."""
    rate = Decimal(str(settings.invoice_vat_percent)) / Decimal("100")
    net = Decimal("0")
    for item in request.items:
        net += Decimal(str(item.price or 0)) * int(item.quantity or 0)
    net = _q(net)
    vat = _q(net * rate)
    gross = _q(net + vat)
    percent = int(request.payment_percent or 100)
    prepay = _q(gross * Decimal(percent) / Decimal("100"))
    return {
        "net": net,
        "vat": vat,
        "gross": gross,
        "percent": percent,
        "prepay": prepay,
        "remainder": _q(gross - prepay),
    }


def build_invoice_pdf(request) -> bytes | None:
    """Zayavka uchun счёт на оплату PDF baytlarini qaytaradi.

    None => rekvizitlar to'liq emas yoki shrift topilmadi (yarim hujjat yubormaymiz).
    `request` da items/pharmacy/contract EAGER-LOAD bo'lishi shart."""
    if not settings.invoice_ready() or not _register_fonts():
        return None

    amounts = invoice_amounts(request)
    rate = Decimal(str(settings.invoice_vat_percent)) / Decimal("100")
    vat_label = f"НДС ({settings.invoice_vat_percent}%)"

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
        title=f"Счет на оплату № {request.id}",
    )
    base = getSampleStyleSheet()["Normal"]
    normal = ParagraphStyle("n", parent=base, fontName=FONT, fontSize=8.5, leading=11)
    small = ParagraphStyle("s", parent=normal, fontSize=7.5, leading=9.5)
    bold = ParagraphStyle("b", parent=normal, fontName=FONT_BOLD)
    title = ParagraphStyle("t", parent=normal, fontName=FONT_BOLD, fontSize=12, alignment=TA_CENTER, leading=16)
    cell = ParagraphStyle("c", parent=normal, fontSize=7.5, leading=9)
    cell_r = ParagraphStyle("cr", parent=cell, alignment=2)

    story = []

    # ---- Shapka: rekvizitlar. Namunadagi tartib, faqat "Банк получателя"
    # qatori YO'Q (foydalanuvchi qarori), oxiriga manzil/telefon/ОКЭД qo'shildi.
    head = [
        [Paragraph("ИНН:", small), Paragraph(settings.invoice_inn, small)],
        [Paragraph("Р/С Поставщика:", small), Paragraph(settings.invoice_account, small)],
        [Paragraph("Получатель:", small), Paragraph(settings.invoice_company, small)],
        [Paragraph("МФО банка:", small), Paragraph(settings.invoice_mfo, small)],
    ]
    # Ixtiyoriy qatorlar — sozlamada bo'lsagina chiqadi.
    for label, value in (
        ("Адрес:", settings.invoice_address),
        ("Телефон:", settings.invoice_phone),
        ("ОКЭД:", settings.invoice_oked),
    ):
        if value:
            head.append([Paragraph(label, small), Paragraph(value, small)])
    head_tbl = Table(head, colWidths=[35 * mm, 145 * mm])
    head_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story += [head_tbl, Spacer(1, 6 * mm)]

    # ---- Sarlavha ----
    date = request.created_at.strftime("%d.%m.%Y") if request.created_at else "-"
    story += [Paragraph(f"Счет на оплату № {request.id} от {date} г.", title), Spacer(1, 4 * mm)]

    # ---- Поставщик / Покупатель / Основание ----
    ph = request.pharmacy
    buyer = ph.name if ph else "-"
    if ph is not None and ph.filial:
        buyer += f" ({ph.filial})"
    buyer_parts = [buyer]
    if ph is not None and ph.inn:
        buyer_parts.append(f"ИНН: {ph.inn}")
    if ph is not None and ph.location_text:
        buyer_parts.append(f"Адрес: {ph.location_text}")

    story += [
        Paragraph("Поставщик:", bold),
        Paragraph(f"{settings.invoice_company}, ИНН: {settings.invoice_inn}", normal),
        Spacer(1, 2 * mm),
        Paragraph("Покупатель:", bold),
        Paragraph(", ".join(buyer_parts), normal),
        Spacer(1, 2 * mm),
        Paragraph("Основание:", bold),
    ]
    if request.contract is not None:
        c_date = request.contract.signed_date.strftime("%d.%m.%Y") if request.contract.signed_date else "-"
        story.append(Paragraph(f"Договор поставки № {request.contract.number} от {c_date} г.", normal))
    else:
        story.append(Paragraph("Без договора", normal))
    story.append(Spacer(1, 4 * mm))

    # ---- Tovarlar jadvali ----
    header = ["№", "Товары (работы, услуги)", "Кол-во", "Цена с НДС\n(сум)",
              f"Сумма без НДС\n(сум)", f"{vat_label}", "Сумма с НДС\n(сум)"]
    rows = [[Paragraph(h, ParagraphStyle("h", parent=cell, fontName=FONT_BOLD, alignment=TA_CENTER)) for h in header]]

    total_qty = 0
    for i, item in enumerate(request.items, 1):
        qty = int(item.quantity or 0)
        price_net = Decimal(str(item.price or 0))
        price_gross = _q(price_net * (Decimal("1") + rate))
        line_net = _q(price_net * qty)
        line_vat = _q(line_net * rate)
        line_gross = _q(line_net + line_vat)
        total_qty += qty
        rows.append([
            Paragraph(str(i), cell),
            Paragraph(item.drug_name or "-", cell),
            Paragraph(f"{qty} шт.", cell_r),
            Paragraph(_money(price_gross), cell_r),
            Paragraph(_money(line_net), cell_r),
            Paragraph(_money(line_vat), cell_r),
            Paragraph(_money(line_gross), cell_r),
        ])
    rows.append([
        Paragraph("", cell), Paragraph("Итого:", ParagraphStyle("i", parent=cell, fontName=FONT_BOLD)),
        Paragraph(f"{total_qty} шт.", ParagraphStyle("ir", parent=cell_r, fontName=FONT_BOLD)),
        Paragraph("", cell),
        Paragraph(_money(amounts["net"]), ParagraphStyle("ir2", parent=cell_r, fontName=FONT_BOLD)),
        Paragraph(_money(amounts["vat"]), ParagraphStyle("ir3", parent=cell_r, fontName=FONT_BOLD)),
        Paragraph(_money(amounts["gross"]), ParagraphStyle("ir4", parent=cell_r, fontName=FONT_BOLD)),
    ])

    tbl = Table(rows, colWidths=[8 * mm, 58 * mm, 16 * mm, 24 * mm, 26 * mm, 22 * mm, 26 * mm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.92, 0.92, 0.92)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [tbl, Spacer(1, 4 * mm)]

    # ---- Yakuniy summalar ----
    story += [
        Paragraph(
            f"Всего наименований {len(request.items)}, на сумму {_money(amounts['gross'])} сум.", normal
        ),
        Paragraph(f"В том числе {vat_label}: {_money(amounts['vat'])} сум.", normal),
    ]
    # 50% shartida: invoys to'liq summaga, lekin hozir to'lanadigan qism aniq ko'rsatiladi.
    if amounts["percent"] != 100:
        story += [
            Spacer(1, 2 * mm),
            Paragraph(
                f"К оплате ({amounts['percent']}% предоплата): {_money(amounts['prepay'])} сум.", bold
            ),
            Paragraph(f"Остаток к доплате: {_money(amounts['remainder'])} сум.", normal),
        ]
    story.append(Spacer(1, 12 * mm))

    # ---- Imzolar ----
    story += [
        Paragraph("Руководитель: ____________________ ( подпись )", normal),
        Spacer(1, 6 * mm),
        Paragraph("Бухгалтер: ____________________ ( подпись )", normal),
    ]

    doc.build(story)
    return buf.getvalue()
