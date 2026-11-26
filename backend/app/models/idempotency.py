"""Claves de idempotencia persistentes para escrituras (P0-03 de la guia).

Una clave identifica un intento de escritura de un usuario sobre un endpoint.
Mientras la operacion esta en curso la fila queda en ``in_progress``; al
confirmarse la transaccion pasa a ``completed`` con la respuesta exacta que se
devolvio, de modo que un reintento con la misma clave y el mismo payload
devuelve la misma respuesta sin duplicar fiados, ventas ni pagos.
"""

from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class IdempotencyKey(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "key", "user_id", "scope", name="uq_idempotency_keys_actor_scope"
        ),
    )

    key: Mapped[str] = mapped_column(String(120), nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scope: Mapped[str] = mapped_column(String(60), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[dict | None] = mapped_column(JSON)
    resource_id: Mapped[UUID | None] = mapped_column()
