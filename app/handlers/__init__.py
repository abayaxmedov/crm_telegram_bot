from __future__ import annotations

from aiogram import Dispatcher

from app.handlers import (
    admin,
    common,
    diary,
    directories,
    finance,
    operator,
    rep_finance,
    reports,
    requests,
    salary,
    sales,
    warehouse,
)


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(admin.router)
    dp.include_router(directories.router)
    dp.include_router(reports.router)
    dp.include_router(requests.router)
    # Медвакил (медпредставитель) — rep routerlar finance/salary/common'dan oldin.
    dp.include_router(sales.router)
    dp.include_router(warehouse.router)
    dp.include_router(diary.router)
    dp.include_router(rep_finance.router)
    dp.include_router(operator.router)
    dp.include_router(finance.router)
    dp.include_router(salary.router)
    dp.include_router(common.router)
