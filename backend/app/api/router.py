from fastapi import APIRouter

from app.api.routes import (
    academic_ml,
    academic_ml_v4,
    academic_ml_v6,
    auth,
    clients,
    credits,
    payments,
    products,
    proy_experimental,
    reports,
    sales,
    settings,
    users,
    webauthn,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(academic_ml.router)
api_router.include_router(academic_ml_v4.router)
api_router.include_router(academic_ml_v6.router)
api_router.include_router(auth.router)
api_router.include_router(webauthn.router)
api_router.include_router(users.router)
api_router.include_router(clients.router)
api_router.include_router(products.router)
api_router.include_router(sales.router)
api_router.include_router(credits.router)
api_router.include_router(payments.router)
api_router.include_router(proy_experimental.router)
api_router.include_router(settings.router)
api_router.include_router(reports.router)
api_router.include_router(whatsapp.router)
