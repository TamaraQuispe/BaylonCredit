from fastapi import APIRouter

from app.api.routes import (
    auth,
    clients,
    credits,
    payments,
    products,
    reports,
    sales,
    settings,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(clients.router)
api_router.include_router(products.router)
api_router.include_router(sales.router)
api_router.include_router(credits.router)
api_router.include_router(payments.router)
api_router.include_router(settings.router)
api_router.include_router(reports.router)
