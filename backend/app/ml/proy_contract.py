"""Contrato versionado de datos de PROY (P0-04 de la guia de traspaso).

Los modulos historicos ``features.py`` y ``outcomes.py`` quedan congelados y son
la referencia de lo que calculo V6. Este modulo **describe** ese contrato con
nombre, definicion, unidad, fuente y rango, y valida snapshots antes de que un
modelo los consuma.

No reemplaza al selector historico ni cambia su semantica: si PROY redefine una
variable o el corte del target, debe crear una version nueva (``contract_version``
distinta) y reentrenar con datos compatibles, en lugar de editar los modulos
congelados y seguir llamandolo V6.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from math import isfinite

CONTRACT_VERSION = "proy-credit-contract-v1"
SNAPSHOT_RULE = (
    "Todas las features son estrictamente anteriores al momento de evaluar."
)

#: Zona y corte del target. El informe declaro las 20:00 como supuesto, no como
#: confirmacion exacta del propietario; PROY debe acordarlo y versionarlo.
TARGET_TIMEZONE = "America/Lima"
TARGET_CUTOFF_HOUR_LOCAL = 20
TARGET_GRACE_DAYS = 3


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    definition: str
    unit: str
    source: str
    minimum: float
    maximum: float | None = None
    integer: bool = False
    note: str | None = None


FEATURE_SPECS: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        name="completed_sales",
        definition="Ventas enlazadas al cliente en cualquier modo de pago.",
        unit="ventas",
        source="sales.client_id",
        minimum=0,
        integer=True,
        note=(
            "Una venta al contado de la API normal no se enlaza al cliente; un fiado "
            "directo tiene sale_id nulo. No afirmar que siempre cuenta compras de contado."
        ),
    ),
    FeatureSpec(
        name="paid_credits",
        definition="Fiados del cliente con saldo pendiente igual a cero.",
        unit="fiados",
        source="credits.pending_amount = 0",
        minimum=0,
        integer=True,
        note="Un fiado directo puede aumentar paid_credits sin aumentar completed_sales.",
    ),
    FeatureSpec(
        name="paid_late",
        definition="Fiados liquidados cuyo ultimo pago fue posterior al vencimiento.",
        unit="fiados",
        source="payments.payment_date > credits.due_date",
        minimum=0,
        integer=True,
        note=(
            "Solo desenlaces observados antes de la solicitud; "
            "una gracia no vuelve puntual un atraso."
        ),
    ),
    FeatureSpec(
        name="pending_overdue",
        definition="Fiados con saldo pendiente y vencimiento anterior a hoy.",
        unit="fiados",
        source="credits.pending_amount > 0 and due_date < hoy",
        minimum=0,
        integer=True,
    ),
    FeatureSpec(
        name="pending_current",
        definition="Fiados con saldo pendiente y vencimiento hoy o posterior.",
        unit="fiados",
        source="credits.pending_amount > 0 and due_date >= hoy",
        minimum=0,
        integer=True,
    ),
    FeatureSpec(
        name="outstanding",
        definition="Suma del saldo pendiente de todos los fiados del cliente.",
        unit="S/ (Decimal)",
        source="sum(credits.pending_amount)",
        minimum=0,
        note="Un abono no es liquidacion: solo la liquidacion total restituye elegibilidad.",
    ),
    FeatureSpec(
        name="utilization",
        definition="outstanding / max_credit_amount; 0 si no hay tope configurado.",
        unit="ratio 0-1",
        source="derivada",
        minimum=0,
        maximum=1,
    ),
    FeatureSpec(
        name="requested_ratio",
        definition="Monto solicitado / max_credit_amount; 1.0 si no hay tope configurado.",
        unit="ratio (puede superar 1)",
        source="derivada",
        minimum=0,
        note="S/ 80 es referencia de la simulacion, no un maximo real del negocio.",
    ),
    FeatureSpec(
        name="tenure_days",
        definition="Dias desde el registro del cliente hasta hoy.",
        unit="dias",
        source="clients.created_at",
        minimum=0,
        integer=True,
        note="Frontera de dia: se calcula con date.today() local frente a created_at en UTC.",
    ),
    FeatureSpec(
        name="punctuality_rate",
        definition="(paid_credits - paid_late) / paid_credits; 0 si no hay fiados pagados.",
        unit="ratio 0-1",
        source="derivada",
        minimum=0,
        maximum=1,
    ),
    FeatureSpec(
        name="overdue_rate",
        definition="pending_overdue / (pending_overdue + pending_current); 0 si no hay activos.",
        unit="ratio 0-1",
        source="derivada",
        minimum=0,
        maximum=1,
    ),
)

FEATURE_NAMES_PROY: tuple[str, ...] = tuple(spec.name for spec in FEATURE_SPECS)


@dataclass(frozen=True)
class TargetSpec:
    name: str
    definition: str
    positive_label: str
    negative_label: str
    unknown_rule: str


TARGET_SPEC = TargetSpec(
    name="late_payment",
    definition=(
        "No estar totalmente pagado al terminar la fecha contractual "
        "(1 = atraso, 0 = pagado dentro del plazo)."
    ),
    positive_label="atraso",
    negative_label="puntual",
    unknown_rule=(
        "Saldo pendiente aun dentro del vencimiento, sin fecha de liquidacion confiable "
        "o con pago posterior al corte: desconocido (None), nunca clase 0."
    ),
)


def target_cutoff(observed_on: date) -> date:
    """Corte contractual mas dias de gracia, en fecha de negocio."""
    return observed_on + timedelta(days=TARGET_GRACE_DAYS)


def validate_feature_snapshot(values: Mapping[str, float]) -> list[str]:
    """Devuelve la lista de incumplimientos del contrato (vacia si es valido)."""
    problems: list[str] = []
    provided = set(values)
    expected = set(FEATURE_NAMES_PROY)
    for missing in sorted(expected - provided):
        problems.append(f"Falta la feature obligatoria '{missing}'.")
    for unknown in sorted(provided - expected):
        problems.append(f"Feature no declarada en el contrato: '{unknown}'.")

    for spec in FEATURE_SPECS:
        if spec.name not in values:
            continue
        raw = values[spec.name]
        try:
            value = float(raw)
        except (TypeError, ValueError):
            problems.append(f"'{spec.name}' no es numerica: {raw!r}.")
            continue
        if not isfinite(value):
            problems.append(f"'{spec.name}' no puede ser NaN ni infinito.")
            continue
        if value < spec.minimum:
            problems.append(f"'{spec.name}' = {value} es menor que {spec.minimum}.")
        if spec.maximum is not None and value > spec.maximum:
            problems.append(f"'{spec.name}' = {value} supera el maximo {spec.maximum}.")
        if spec.integer and value != int(value):
            problems.append(f"'{spec.name}' = {value} debe ser un conteo entero.")
    return problems


def snapshot_is_valid(values: Mapping[str, float]) -> bool:
    return not validate_feature_snapshot(values)


def describe_contract() -> dict:
    """Resumen serializable para anexos y trazabilidad de la entrega."""
    return {
        "contract_version": CONTRACT_VERSION,
        "snapshot_rule": SNAPSHOT_RULE,
        "target": {
            "name": TARGET_SPEC.name,
            "definition": TARGET_SPEC.definition,
            "timezone": TARGET_TIMEZONE,
            "cutoff_hour_local": TARGET_CUTOFF_HOUR_LOCAL,
            "grace_days": TARGET_GRACE_DAYS,
            "unknown_rule": TARGET_SPEC.unknown_rule,
        },
        "features": [
            {
                "name": spec.name,
                "definition": spec.definition,
                "unit": spec.unit,
                "source": spec.source,
                "minimum": spec.minimum,
                "maximum": spec.maximum,
                "integer": spec.integer,
                "note": spec.note,
            }
            for spec in FEATURE_SPECS
        ],
    }


def outstanding_is_blocking(outstanding: Decimal) -> bool:
    """Regla del propietario: cualquier saldo pendiente mayor que cero bloquea."""
    return Decimal(outstanding) > 0
