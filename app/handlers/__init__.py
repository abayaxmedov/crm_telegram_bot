from __future__ import annotations

from aiogram import Dispatcher

from app.handlers import (
    admin,
    ball,
    cancel,
    common,
    diary,
    directories,
    drugs_admin,
    finance,
    materials,
    operator,
    regions,
    rep_finance,
    reports,
    reports_view,
    requests,
    salary,
    sales,
    warehouse,
    webapp_link,
)


def setup_routers(dp: Dispatcher) -> None:
    # BIRINCHI: FSM holatida menyu tugmasi bosilsa oqimni bekor qiladi
    # (holat bo'lmasa SkipHandler bilan keyingi routerlarga o'tkazadi).
    dp.include_router(cancel.router)
    dp.include_router(admin.router)
    dp.include_router(regions.router)
    dp.include_router(drugs_admin.router)
    dp.include_router(ball.router)
    dp.include_router(webapp_link.router)
    dp.include_router(directories.router)
    dp.include_router(reports.router)
    dp.include_router(reports_view.router)
    dp.include_router(materials.router)
    dp.include_router(requests.router)
    # Sotuvchilar (medvakil + regional) — rep routerlar finance/salary/common'dan oldin.
    dp.include_router(sales.router)
    dp.include_router(warehouse.router)
    dp.include_router(diary.router)
    dp.include_router(rep_finance.router)
    dp.include_router(operator.router)
    dp.include_router(finance.router)
    dp.include_router(salary.router)
    dp.include_router(common.router)
