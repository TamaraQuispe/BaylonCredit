from asyncio import Task, create_task, gather
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.http_logging import RequestLoggingMiddleware
from app.db.session import SERVICE_UNAVAILABLE_MESSAGE, DatabaseUnavailable
from app.services.credit_review import review_expiry_loop
from app.services.whatsapp import reminder_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    reminder_task: Task | None = None
    if settings.whatsapp_enabled and settings.whatsapp_notify_reminders:
        reminder_task = create_task(reminder_loop(settings.whatsapp_reminder_interval_hours))
    review_expiry_task: Task | None = None
    if settings.credit_review_expiry_interval_minutes > 0:
        review_expiry_task = create_task(
            review_expiry_loop(settings.credit_review_expiry_interval_minutes)
        )
    yield
    tasks = [task for task in (reminder_task, review_expiry_task) if task is not None]
    for task in tasks:
        task.cancel()
    if tasks:
        await gather(*tasks, return_exceptions=True)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(DatabaseUnavailable)
async def database_unavailable_handler(_request, _error):
    return JSONResponse(
        status_code=503,
        content={"detail": SERVICE_UNAVAILABLE_MESSAGE, "code": "database_unavailable"},
        headers={"Retry-After": "5"},
    )


app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
