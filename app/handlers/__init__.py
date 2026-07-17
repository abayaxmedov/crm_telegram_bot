from __future__ import annotations

from aiogram import Dispatcher

from app.handlers import (
    admin,
    ball,
    cancel,
    common,
    directories,
    drugs_admin,
    finance,
    gift,
    listing,
    lpu,
    materials,
    operator,
    regions,
    rep_finance,
    reports,
    reports_view,
    requests,
    salary,
    sales,
    top_approvals,
    warehouse,
    webapp_link,
    wholesale_income,
    wholesalers,
)


def setup_routers(dp: Dispatcher) -> None:
    # BIRINCHI: FSM holatida menyu tugmasi bosilsa oqimni bekor qiladi
    # (holat bo'lmasa SkipHandler bilan keyingi routerlarga o'tkazadi).
    dp.include_router(cancel.router)
    # Sahifalangan ro'yxatlar (navigatsiya/qidiruv/karta) — feature routerlardan oldin.
    dp.include_router(listing.router)
    dp.include_router(admin.router)
    dp.include_router(regions.router)
    dp.include_router(drugs_admin.router)
    dp.include_router(wholesalers.router)
    dp.include_router(ball.router)
    dp.include_router(gift.router)
    dp.include_router(webapp_link.router)
    dp.include_router(directories.router)
    dp.include_router(lpu.router)
    dp.include_router(reports.router)
    dp.include_router(reports_view.router)
    dp.include_router(materials.router)
    dp.include_router(requests.router)
    # Sotuvchilar (medvakil + regional) — rep routerlar finance/salary/common'dan oldin.
    dp.include_router(sales.router)
    dp.include_router(warehouse.router)
    dp.include_router(wholesale_income.router)
    dp.include_router(rep_finance.router)
    dp.include_router(top_approvals.router)
    dp.include_router(operator.router)
    dp.include_router(finance.router)
    dp.include_router(salary.router)
    dp.include_router(common.router)
