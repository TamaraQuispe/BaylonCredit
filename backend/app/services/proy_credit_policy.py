"""Politica PROY de saldo pendiente (P0-02 de la guia de traspaso).

Regla del propietario: cualquier saldo pendiente mayor que cero, sea vigente,
parcial o con acuerdo, impide evaluar y conceder un nuevo fiado. Se aplica por
igual al credito directo y a la venta al credito.

El bloqueo es duro: ``manual_override`` y el rol administrador no lo levantan
mientras exista deuda. Pagar todo solo restituye elegibilidad; nunca aprueba ni
recomienda un monto.

La compuerta es determinista y se resuelve antes del modelo: cuando bloquea, no
se calcula probabilidad de atraso ni se llama al clasificador.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.commerce import Credit

PENDING_BALANCE_BLOCK = "BLOCKED_PENDING_BALANCE"
ELIGIBLE_FOR_RISK_ASSESSMENT = "ELIGIBLE_FOR_RISK_ASSESSMENT"


@dataclass(frozen=True)
class PendingBalanceGate:
    decision: str
    pending_amount: Decimal
    reason: str | None


def gate_from_pending(pending_amount: Decimal) -> PendingBalanceGate:
    """Decide la compuerta a partir del saldo pendiente ya calculado."""
    pending = Decimal(pending_amount)
    if pending > 0:
        return PendingBalanceGate(
            decision=PENDING_BALANCE_BLOCK,
            pending_amount=pending,
            reason=(
                f"Bloqueo por saldo pendiente de S/ {pending}: el cliente mantiene deuda "
                "vigente, parcial o con acuerdo. No se evalua un nuevo fiado hasta observar "
                "la liquidacion total; la excepcion manual no levanta este bloqueo."
            ),
        )
    return PendingBalanceGate(
        decision=ELIGIBLE_FOR_RISK_ASSESSMENT,
        pending_amount=Decimal("0"),
        reason=None,
    )


async def lock_client(db: AsyncSession, client_id: UUID) -> Client | None:
    """Bloquea la fila del cliente dentro de la transaccion en curso."""
    return await db.scalar(
        select(Client).where(Client.id == client_id).with_for_update()
    )


async def pending_balance(db: AsyncSession, client_id: UUID) -> Decimal:
    """Saldo pendiente autoritativo del cliente, leido de la base con Decimal."""
    total = await db.scalar(
        select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
            Credit.client_id == client_id,
            Credit.pending_amount > 0,
        )
    )
    return Decimal(total or 0)


async def pending_balance_gate(db: AsyncSession, client_id: UUID) -> PendingBalanceGate:
    return gate_from_pending(await pending_balance(db, client_id))
