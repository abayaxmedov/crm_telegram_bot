from __future__ import annotations

from aiogram import Dispatcher

from app.handlers import admin, common, directories, finance, reports, requests, salary


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(admin.router)
    dp.include_router(directories.router)
    dp.include_router(reports.router)
    dp.include_router(requests.router)
    dp.include_router(finance.router)
    dp.include_router(salary.router)
    dp.include_router(common.router)

