from asyncio import Task, create_task
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.http_logging import RequestLoggingMiddleware
from app.services.whatsapp import reminder_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    reminder_task: Task | None = None
    if settings.whatsapp_enabled and settings.whatsapp_notify_reminders:
        reminder_task = create_task(reminder_loop(settings.whatsapp_reminder_interval_hours))
    yield
    if reminder_task:
        reminder_task.cancel()


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
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
