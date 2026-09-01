from fastapi import APIRouter

from app.api.routes import auth, clients, products, sales, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(clients.router)
api_router.include_router(products.router)
api_router.include_router(sales.router)
