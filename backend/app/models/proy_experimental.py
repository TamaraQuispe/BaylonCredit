"""Resultados experimentales PROY: no son una aprobacion ni un credito."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class ProyExperimentalEvaluation(UUIDMixin, TimestampMixin, Base):
    """Traza de una inferencia PROY sobre historial real.

    Vive aparte de ``credit_evaluations`` a proposito: el modelo es
    ``research_only`` y estos registros no deben contarse como evaluaciones del
    negocio, no entran a la cola de revisiones y nunca crean un fiado.
    """

    __tablename__ = "proy_experimental_evaluations"

    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    pending_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    probability: Mapped[float | None] = mapped_column(Float)
    threshold: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    predicted: Mapped[int | None] = mapped_column(Integer)
    model_called: Mapped[bool] = mapped_column(Boolean, nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    feature_snapshot: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
