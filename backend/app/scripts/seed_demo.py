"""Seed the isolated demo database with deterministic fictional records.

This is a UI/data demo seed for the Cerveceria Baylon academic environment.
Everything it writes is invented: names, documents, phones, addresses, sales,
credits and payments. No real customer or personal data is used or copied. The seed reuses the ten
catalog products pre-loaded by migration ``20260901_0002_commerce`` (P001-P010)
and never inserts products, SKUs or categories of its own.

Determinism and safety properties:

* All identifiers, UUIDs and codes are derived from fixed constants, so a
  rerun produces exactly the same logical dataset. Base records are never
  created twice: if the marker sale already exists, they are left untouched
  (including the ``docente@example.com`` account); any missing newcomer
  clients from the roster and their records are backfilled once.
* Document numbers use the 9xxxxxxx range, which is not assigned to real
  Peruvian DNIs (current issuance is well below 9xxxxxxx). Phone numbers use
  the ``+51 900 000 0xx`` block, which is reserved for documentation-style
  examples and not reachable. RUC-style identifiers are not used at all.
* Dates are fixed between 2026-09-02 and 2026-10-28. ``REFERENCE_DATE`` is the
  fixed "as of" day used to derive overdue vs. current credits, so results do
  not depend on the clock of the machine running the seed.
* The seed does NOT create credit evaluations and is not used to build or
  validate ML models; risk/score/limit values on credits are display data
  only, so the demo dashboards render coherent information.
* Credit totals never exceed the configured per-credit cap
  (``max_credit_amount`` = 200).

Distribution of the 32 seeded credits: ~30/45/25 across paid (10), pending
overdue (15) and pending current (7), with on-time and late payments, as well
as partial payments ("abonos") for overdue credits. The four newcomer clients
(90000025-90000028) were appended after the original 24 so the base records
keep the exact same codes and identifiers they had before.
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import NAMESPACE_OID, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.client import Client
from app.models.commerce import (
    Credit,
    CreditStatus,
    InventoryMovement,
    InventoryMovementType,
    Payment,
    PaymentAllocation,
    PaymentMode,
    Product,
    RiskLevel,
    Sale,
    SaleItem,
)
from app.models.settings import DEFAULT_ORGANIZATION_ID, SETTINGS_ID, BusinessSettings
from app.models.user import User, UserRole

LIMA = timezone(timedelta(hours=-5))
CENT = Decimal("0.01")
TAX_RATE = Decimal("0.18")
REFERENCE_DATE = date(2026, 11, 15)
SALES_FIRST_DATE = date(2026, 9, 2)
SALES_LAST_DATE = date(2026, 10, 28)
SEED_NAMESPACE = uuid5(NAMESPACE_OID, "credify.demo.seed")
MARKER_SALE_CODE = "V-2026-0001"


def _seed_id(kind: str, key: str) -> UUID:
    return uuid5(SEED_NAMESPACE, f"baylon-demo:{kind}:{key}")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _moment(day: date, hour: int = 10, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=LIMA)


# The seed reuses only the catalog products pre-loaded by migration 0002; it never
# inserts products of its own. Their prices are duplicated here only so the plan can
# be computed without a database round trip.
MIGRATION_PRODUCT_PRICES = {
    "P001": Decimal("6.50"),
    "P002": Decimal("7.00"),
    "P003": Decimal("4.00"),
    "P004": Decimal("8.50"),
    "P005": Decimal("12.00"),
    "P006": Decimal("35.00"),
    "P007": Decimal("120.00"),
    "P008": Decimal("12.00"),
    "P009": Decimal("2.50"),
    "P010": Decimal("6.00"),
}

# Fictional neighbors of the brewery: bodegas, bares, licorerias, pollerias and
# cevicherias across Lima. Names and addresses are invented.
EXTRA_CLIENT_SPECS = [
    ("90000029", "Luis Eduardo", "Huamani Salazar", "Bodega La Huaca",
     "+51 900 000 029", "Av. Brasil 2301, Jesus Maria, Lima"),
    ("90000030", "Rosa Eugenia", "Cuellar Figueroa", "Minimarket La Parada",
     "+51 900 000 030", "Jr. Huanuco 385, La Victoria, Lima"),
    ("90000031", "Mario Javier", "Chumpitaz Vargas", "Cevicheria El Buen Punto",
     "+51 900 000 031", "Av. Aviacion 2208, San Borja, Lima"),
    ("90000032", "Elena Patricia", "Cordova Barrios", "Bodega Marazon",
     "+51 900 000 032", "Av. Parinacochas 930, La Victoria, Lima"),
    ("90000033", "Victor Manuel", "Paz Hidalgo", "Licoreria Blockhouse",
     "+51 900 000 033", "Av. Tahuantinsuyo 620, San Juan de Lurigancho, Lima"),
    ("90000034", "Carmen Delia", "Quispe Huaynates", "Polleria Doña Delia",
     "+51 900 000 034", "Av. Canada 2450, San Miguel, Lima"),
    ("90000035", "Walter Segundo", "Untiveros Tello", "Bodega San Martincito",
     "+51 900 000 035", "Jr. Aguarico 721, Rimac, Lima"),
    ("90000036", "Patricia Lorena", "Espinoza Rios", "Minimarket La Equis",
     "+51 900 000 036", "Av. Nicolas Arriola 1340, La Victoria, Lima"),
    ("90000037", "Jose Antonio", "Zeballos Vega", "Bar La Colmena",
     "+51 900 000 037", "Jr. Ica 421, Surquillo, Lima"),
    ("90000038", "Juan Carlos", "Monge Cardenas", "Bodega Terra",
     "+51 900 000 038", "Av. Tupac Amaru 780, Rimac, Lima"),
    ("90000039", "Ana Maria", "Narvaez Quispe", "Cevicheria El Buen Sabor",
     "+51 900 000 039", "Av. Santa Anita 1239, Santa Anita, Lima"),
    ("90000040", "Milagros Rocio", "Centeno Martinez", "Bodega La Rivera",
     "+51 900 000 040", "Av. La Mar 760, Pueblo Libre, Lima"),
    ("90000041", "Roberto Jesus", "Pariona Alegria", "Licoreria Don Roberto",
     "+51 900 000 041", "Av. Tomas Marsano 1302, Surquillo, Lima"),
    ("90000042", "Diana Carolina", "Valdivia Osorio", "Bodega Santa Maria",
     "+51 900 000 042", "Av. Venezuela 2190, Cercado de Lima, Lima"),
    ("90000043", "Raul Enrique", "Briones Pineda", "Minimarket El Chaska",
     "+51 900 000 043", "Av. Argentina 2182, Cercado de Lima, Lima"),
    ("90000044", "Cecilia Victoria", "Vasquez Alban", "Bodega Costamar",
     "+51 900 000 044", "Av. Colonial 3190, Cercado de Lima, Lima"),
    ("90000045", "Miguel Angel", "Ponte Mendoza", "Cevicheria Don Miguel",
     "+51 900 000 045", "Av. Tomas Valle 1208, Los Olivos, Lima"),
    ("90000046", "Ruth Nancy", "Hernandez Alarcon", "Bodega La Loma",
     "+51 900 000 046", "Av. Brasil 2578, Jesus Maria, Lima"),
    ("90000047", "David Alejandro", "Choque Ordonez", "Licoreria Chato",
     "+51 900 000 047", "Av. Santa Rosa 360, La Perla, Callao"),
    ("90000048", "Luisa Fernanda", "Lozano Medina", "Bodega La Villita",
     "+51 900 000 048", "Jr. Callao 605, El Agustino, Lima"),
    ("90000049", "Percy Ricardo", "Camacho Turpo", "Minimarket Los Jardines",
     "+51 900 000 049", "Av. Bolivia 428, La Victoria, Lima"),
    ("90000050", "Gabriela Ines", "Rodriguez Luna", "Bodega San Andres",
     "+51 900 000 050", "Av. Carlos Izaguirre 985, Los Olivos, Lima"),
]

def _build_extra_credit_sales():
    from datetime import timedelta
    profiles = [
        # date, items, delay_days, partial_ratio
        (date(2026, 9, 9), [("P003", 8)], 0, None),
        (date(2026, 9, 12), [("P009", 20)], 0, None),
        (date(2026, 9, 14), [("P002", 5)], 2, None),
        (date(2026, 9, 17), [("P004", 4)], 0, None),
        (date(2026, 9, 18), [("P003", 10)], 0, Decimal("0.50")),
        (date(2026, 9, 21), [("P001", 10)], 4, None),
        (date(2026, 9, 22), [("P005", 1)], 3, Decimal("0.40")),
        (date(2026, 9, 24), [("P009", 18)], 0, None),
        (date(2026, 9, 26), [("P010", 2)], 5, None),
        (date(2026, 9, 28), [("P002", 6)], 2, Decimal("0.60")),
        (date(2026, 9, 29), [("P004", 3)], 0, None),
        (date(2026, 10, 1), [("P003", 16)], 3, None),
        (date(2026, 10, 3), [("P001", 8)], 8, Decimal("0.45")),
        (date(2026, 10, 5), [("P009", 14)], 2, None),
        (date(2026, 10, 7), [("P006", 1)], 0, Decimal("0.50")),
        (date(2026, 10, 8), [("P002", 8)], 6, None),
        (date(2026, 10, 10), [("P001", 6)], 1, None),
        (date(2026, 10, 12), [("P010", 2)], 4, Decimal("0.35")),
        (date(2026, 10, 13), [("P003", 9)], 0, None),
        (date(2026, 10, 16), [("P005", 1)], 9, None),
        (date(2026, 10, 19), [("P009", 12)], 0, Decimal("0.40")),
        (date(2026, 10, 22), [("P007", 1)], 0, None),
    ]
    sales = []
    for offset, (day, items, delay, partial_ratio) in enumerate(profiles):
        client = EXTRA_CLIENT_SPECS[offset][0]
        subtotal = sum(MIGRATION_PRODUCT_PRICES[sku] * qty for sku, qty in items)
        total = _money(subtotal * (Decimal("1") + TAX_RATE))
        risk = RiskLevel.LOW if delay == 0 else RiskLevel.MEDIUM if delay <= 3 else RiskLevel.HIGH
        if partial_ratio is not None:
            risk = RiskLevel.HIGH
        score = 82 - delay * 2 - (10 if partial_ratio else 0)
        payments = []
        if delay == 0 or partial_ratio is not None:
            payment_date = day + timedelta(days=delay + 1)
            if partial_ratio is None:
                payments.append((payment_date, None))
            else:
                payments.append((payment_date, _money(total * partial_ratio)))
        elif delay > 0:
            payment_date = day + timedelta(days=delay + 1)
            payments.append((payment_date, None))
        sales.append({"date": day, "client": client, "items": items,
                      "risk": risk, "score": max(score, 40),
                      "limit": Decimal("200.00"), "term_days": None,
                      "payments": payments})
    return sales

EXTRA_CREDIT_SALES = _build_extra_credit_sales()

CLIENT_SPECS = [
    ("90000001", "Carlos Alberto", "Quispe Mendoza", "Bodega El Tamalito",
     "+51 900 000 001", "Av. Los Alisos 214, Ate, Lima"),
    ("90000002", "Rosa Elena", "Flores Huaman", "Polleria Dona Rosa",
     "+51 900 000 002", "Av. Universitaria 1456, San Luis, Lima"),
    ("90000003", "Jorge Luis", "Ramos Paredes", "Bar La Esquina de Jorge",
     "+51 900 000 003", "Jr. Huanuco 320, La Victoria, Lima"),
    ("90000004", "Maria Fernanda", "Castillo Vargas", "Minimarket La Perla",
     "+51 900 000 004", "Av. Brasil 2210, Jesus Maria, Lima"),
    ("90000005", "Jose Antonio", "Huaman Condori", "Bodega Senor de los Milagros",
     "+51 900 000 005", "Calle Las Flores 88, San Martin de Porres, Lima"),
    ("90000006", "Carmen Rosa", "Vargas Silva", "Licoreria El Roble",
     "+51 900 000 006", "Av. Juan de Aliaga 1335, Brena, Lima"),
    ("90000007", "Miguel Angel", "Paredes Leon", "Cevicheria El Remojo",
     "+51 900 000 007", "Av. La Mar 980, Pueblo Libre, Lima"),
    ("90000008", "Ana Lucia", "Torres Quispe", "Bodega Sol y Luna",
     "+51 900 000 008", "Jr. Aguarico 455, Rimac, Lima"),
    ("90000009", "Luis Alberto", "Mendoza Rojas", "Bar El Rincon del Luis",
     "+51 900 000 009", "Av. Arenales 1820, Lince, Lima"),
    ("90000010", "Rosa Maria", "Huaman Ticona", "Bodega Brisas del Mar",
     "+51 900 000 010", "Av. Proceres de la Independencia 1251, La Victoria, Lima"),
    ("90000011", "Juan Carlos", "Cardenas Poma", "Licoreria Don Juancho",
     "+51 900 000 011", "Av. Venezuela 1450, Cercado de Lima, Lima"),
    ("90000012", "Patricia Elena", "Rios Castillo", "Bodega El Buen Vecino",
     "+51 900 000 012", "Jr. Cuzco 221, Barranco, Lima"),
    ("90000013", "Ernesto Jose", "Delgado Campos", "Bar La Napa",
     "+51 900 000 013", "Av. Circunvalacion 780, San Luis, Lima"),
    ("90000014", "Susana Beatriz", "Leon Paredes", "Minimarket S y B",
     "+51 900 000 014", "Av. Universitaria 3201, Los Olivos, Lima"),
    ("90000015", "Fernando Andres", "Roldan Vega", "Bodega 3 Hermanos",
     "+51 900 000 015", "Calle El Sol 12, San Juan de Lurigancho, Lima"),
    ("90000016", "Gabriela Sofia", "Navarro Diaz", "Ceviche Maria",
     "+51 900 000 016", "Av. Salaverry 1564, Jesus Maria, Lima"),
    ("90000017", "Ricardo Arturo", "Pena Soto", "Bodega El Trebol",
     "+51 900 000 017", "Av. Tomas Marsano 2956, Surquillo, Lima"),
    ("90000018", "Elena Violeta", "Guzman Lara", "Licoreria Violeta",
     "+51 900 000 018", "Av. Aviacion 2380, San Borja, Lima"),
    ("90000019", "Oscar Enrique", "Salcedo Bravo", "Bodega La Esperanza",
     "+51 900 000 019", "Jr. Amazonas 555, Callao"),
    ("90000020", "Veronica Isabel", "Cordero Paz", "Minimarket Vipasa",
     "+51 900 000 020", "Av. Panamericana Sur 9100, Villa El Salvador, Lima"),
    ("90000021", "Hugo Raul", "Tejada Millan", "Bar Los Chasquis",
     "+51 900 000 021", "Av. Tupac Amaru 1430, Rimac, Lima"),
    ("90000022", "Claudia Monica", "Aguilar Ferrer", "Bodega La Esquina",
     "+51 900 000 022", "Jr. Lima 341, Chorrillos, Lima"),
    ("90000023", "Andres Felipe", "Mora Quijano", "Bodega El Mirador",
     "+51 900 000 023", "Av. Nicolas Ayllon 3205, Ate, Lima"),
    ("90000024", "Julia Mercedes", "Rojas Sanchez", "Minimarket Rojas",
     "+51 900 000 024", "Av. Alfredo Mendiola 240, Independencia, Lima"),
    # Newcomer fictional clients, appended after the original roster so the
    # pre-existing 24 keep their exact records. Documents 90000025-90000028.
    ("90000025", "Segundo Esteban", "Huaman Ccahuana", "Bodega El Amanecer",
     "+51 900 000 025", "Jr. Las Violetas 145, Comas, Lima"),
    ("90000026", "Delia Mercedes", "Pinto Mayta", "Minimarket La Colmena",
     "+51 900 000 026", "Jr. Callao 640, El Agustino, Lima"),
    ("90000027", "Teodoro Raul", "Quispe Llamoca", "Cevicheria El Descanso",
     "+51 900 000 027", "Av. Nicolas de Pierola 512, San Juan de Lurigancho, Lima"),
    ("90000028", "Yolanda Beatriz", "Salinas Remuzgo", "Licoreria El Farolito",
     "+51 900 000 028", "Av. Argentina 2540, Cercado de Lima, Lima"),
]
CLIENT_SPECS.extend(EXTRA_CLIENT_SPECS)
NEWCOMER_DOCUMENTS = frozenset({client[0] for client in EXTRA_CLIENT_SPECS}) | {
    "90000025", "90000026", "90000027", "90000028"
}

CASH_LINES = [
    ("P001", 6), ("P003", 8), ("P004", 2), ("P001", 4),     ("P009", 7), ("P002", 4),
    ("P003", 2), ("P001", 12), ("P005", 2), ("P003", 10), ("P002", 2), ("P004", 2),
    ("P001", 2), ("P002", 2), ("P001", 8), ("P010", 2), ("P010", 2), ("P005", 3),
    ("P009", 8), ("P006", 2), ("P003", 6), ("P001", 4), ("P001", 8), ("P002", 2),
    ("P002", 6), ("P010", 2), ("P004", 2), ("P001", 4), ("P003", 10), ("P005", 2),
    ("P001", 12), ("P009", 8), ("P001", 4), ("P003", 8), ("P005", 2), ("P010", 3),
]
CASH_SECOND_LINES = {
    0: ("P005", 2), 4: ("P005", 2), 8: ("P003", 1), 12: ("P005", 2),
    16: ("P005", 2), 20: ("P010", 1), 24: ("P005", 2), 28: ("P005", 2),
    32: ("P009", 1),
}

# term_days: None means the business default (1 day). Bars and cevicherias with a
# commercial relationship get 30 days. Payments: (date, amount); amount None pays
# the whole remaining balance of that credit.
CREDIT_SALES = [

    # --- Paid on time (5) -------------------------------------------------
    {"date": date(2026, 9, 8), "client": "90000001", "items": [("P003", 12)],
     "risk": RiskLevel.LOW, "score": 82, "limit": Decimal("200.00"), "term_days": None,
     "payments": [(date(2026, 9, 8), Decimal("30.00")), (date(2026, 9, 9), None)]},
    {"date": date(2026, 9, 15), "client": "90000006", "items": [("P001", 8)],
     "risk": RiskLevel.LOW, "score": 78, "limit": Decimal("200.00"), "term_days": None,
     "payments": [(date(2026, 9, 16), None)]},
    {"date": date(2026, 9, 24), "client": "90000010", "items": [("P004", 6)],
     "risk": RiskLevel.LOW, "score": 74, "limit": Decimal("200.00"), "term_days": None,
     "payments": [(date(2026, 9, 25), None)]},
    {"date": date(2026, 10, 2), "client": "90000015", "items": [("P001", 10)],
     "risk": RiskLevel.LOW, "score": 85, "limit": Decimal("200.00"), "term_days": None,
     "payments": [(date(2026, 10, 3), None)]},
    {"date": date(2026, 10, 13), "client": "90000020", "items": [("P009", 12)],
     "risk": RiskLevel.LOW, "score": 80, "limit": Decimal("200.00"), "term_days": None,
     "payments": [(date(2026, 10, 14), None)]},
    # --- Paid, but late (4) ------------------------------------------------
    {"date": date(2026, 10, 7), "client": "90000005", "items": [("P003", 6)],
     "risk": RiskLevel.MEDIUM, "score": 64, "limit": Decimal("150.00"), "term_days": None,
     "payments": [(date(2026, 10, 15), None)]},
    {"date": date(2026, 9, 26), "client": "90000012", "items": [("P002", 10)],
     "risk": RiskLevel.MEDIUM, "score": 60, "limit": Decimal("150.00"), "term_days": None,
     "payments": [(date(2026, 10, 5), None)]},
    {"date": date(2026, 10, 15), "client": "90000018", "items": [("P004", 6)],
     "risk": RiskLevel.MEDIUM, "score": 62, "limit": Decimal("150.00"), "term_days": None,
     "payments": [(date(2026, 10, 25), None)]},
    {"date": date(2026, 10, 19), "client": "90000023", "items": [("P006", 1)],
     "risk": RiskLevel.MEDIUM, "score": 58, "limit": Decimal("150.00"), "term_days": None,
     "payments": [(date(2026, 10, 28), None)]},
    # --- Pending overdue with partial abonos (7) ----------------------------
    {"date": date(2026, 10, 6), "client": "90000002", "items": [("P001", 10), ("P009", 4)],
     "risk": RiskLevel.MEDIUM, "score": 55, "limit": Decimal("100.00"), "term_days": None,
     "payments": [(date(2026, 10, 21), Decimal("40.00"))]},
    {"date": date(2026, 9, 30), "client": "90000004", "items": [("P004", 6)],
     "risk": RiskLevel.MEDIUM, "score": 52, "limit": Decimal("100.00"), "term_days": None,
     "payments": [(date(2026, 10, 9), Decimal("25.00")), (date(2026, 10, 23), Decimal("15.00"))]},
    {"date": date(2026, 10, 13), "client": "90000011", "items": [("P002", 12)],
     "risk": RiskLevel.MEDIUM, "score": 54, "limit": Decimal("100.00"), "term_days": None,
     "payments": [(date(2026, 10, 27), Decimal("25.00"))]},
    {"date": date(2026, 10, 18), "client": "90000017", "items": [("P006", 2)],
     "risk": RiskLevel.HIGH, "score": 46, "limit": Decimal("100.00"), "term_days": None,
     "payments": [(date(2026, 10, 28), Decimal("50.00"))]},
    {"date": date(2026, 10, 10), "client": "90000022", "items": [("P001", 9)],
     "risk": RiskLevel.MEDIUM, "score": 56, "limit": Decimal("100.00"), "term_days": None,
     "payments": [(date(2026, 10, 26), Decimal("20.00"))]},
    {"date": date(2026, 9, 19), "client": "90000010", "items": [("P007", 1)],
     "risk": RiskLevel.MEDIUM, "score": 50, "limit": Decimal("150.00"), "term_days": None,
     "payments": [(date(2026, 10, 15), Decimal("53.84"))]},
    {"date": date(2026, 10, 5), "client": "90000006", "items": [("P006", 1)],
     "risk": RiskLevel.HIGH, "score": 48, "limit": Decimal("100.00"), "term_days": None,
     "payments": [(date(2026, 10, 24), Decimal("18.00"))]},
    # --- Pending overdue, no abonos yet (6) ---------------------------------
    {"date": date(2026, 10, 3), "client": "90000008", "items": [("P003", 8)],
     "risk": RiskLevel.HIGH, "score": 44, "limit": Decimal("100.00"), "term_days": None,
     "payments": []},
    {"date": date(2026, 10, 9), "client": "90000014", "items": [("P009", 10)],
     "risk": RiskLevel.HIGH, "score": 46, "limit": Decimal("100.00"), "term_days": None,
     "payments": []},
    {"date": date(2026, 10, 16), "client": "90000019", "items": [("P004", 6)],
     "risk": RiskLevel.HIGH, "score": 45, "limit": Decimal("100.00"), "term_days": None,
     "payments": []},
    {"date": date(2026, 10, 22), "client": "90000024", "items": [("P003", 4)],
     "risk": RiskLevel.HIGH, "score": 43, "limit": Decimal("75.00"), "term_days": None,
     "payments": []},
    {"date": date(2026, 9, 21), "client": "90000005", "items": [("P006", 1)],
     "risk": RiskLevel.HIGH, "score": 42, "limit": Decimal("100.00"), "term_days": None,
     "payments": []},
    {"date": date(2026, 10, 8), "client": "90000012", "items": [("P002", 6)],
     "risk": RiskLevel.HIGH, "score": 45, "limit": Decimal("100.00"), "term_days": None,
     "payments": []},
    # --- Pending current, 30-day commercial terms for bares (6) -------------
    {"date": date(2026, 10, 24), "client": "90000003", "items": [("P001", 12), ("P003", 6)],
     "risk": RiskLevel.LOW, "score": 74, "limit": Decimal("200.00"), "term_days": 30,
     "payments": []},
    {"date": date(2026, 10, 26), "client": "90000007", "items": [("P001", 5)],
     "risk": RiskLevel.LOW, "score": 76, "limit": Decimal("200.00"), "term_days": 30,
     "payments": []},
    {"date": date(2026, 10, 27), "client": "90000013", "items": [("P007", 1)],
     "risk": RiskLevel.MEDIUM, "score": 65, "limit": Decimal("200.00"), "term_days": 30,
     "payments": []},
    {"date": date(2026, 10, 25), "client": "90000016", "items": [("P009", 10)],
     "risk": RiskLevel.LOW, "score": 71, "limit": Decimal("200.00"), "term_days": 30,
     "payments": []},
    {"date": date(2026, 10, 28), "client": "90000021", "items": [("P005", 4)],
     "risk": RiskLevel.MEDIUM, "score": 62, "limit": Decimal("200.00"), "term_days": 30,
     "payments": []},
    {"date": date(2026, 10, 28), "client": "90000003", "items": [("P001", 6)],
     "risk": RiskLevel.LOW, "score": 73, "limit": Decimal("200.00"), "term_days": 30,
     "payments": []},
]

# Newcomer credits for the four added clients. These are processed after every
# base record so the original 64 sales, 28 credits and their codes/identifiers
# never change; the new records continue the sequence (V-2026-0065..0068,
# F-2026-0029..0032). Quantities respect the migration stock left after the
# base records (P001/P006 are sold out; only P002/P003/P004/P005/P007/P009/P010
# have headroom), which is why the newcomer tickets are modest.
NEW_CLIENT_CREDIT_SALES = [
    {"date": date(2026, 10, 19), "client": "90000025", "items": [("P009", 2), ("P003", 1)],
     "risk": RiskLevel.LOW, "score": 79, "limit": Decimal("200.00"), "term_days": None,
     "payments": [(date(2026, 10, 20), None)]},
    {"date": date(2026, 9, 23), "client": "90000026", "items": [("P005", 2)],
     "risk": RiskLevel.MEDIUM, "score": 53, "limit": Decimal("100.00"), "term_days": None,
     "payments": [(date(2026, 10, 8), Decimal("10.00"))]},
    {"date": date(2026, 10, 26), "client": "90000027", "items": [("P007", 1)],
     "risk": RiskLevel.LOW, "score": 75, "limit": Decimal("200.00"), "term_days": 30,
     "payments": []},
    {"date": date(2026, 10, 8), "client": "90000028", "items": [("P002", 1), ("P010", 1)],
     "risk": RiskLevel.HIGH, "score": 47, "limit": Decimal("100.00"), "term_days": None,
     "payments": []},
]

PAYMENT_METHODS = ["Yape/Plin", "Efectivo", "Transferencia"]


@dataclass
class PlanSale:
    code: str
    sale_id: UUID
    day: date
    client_document: str | None
    payment_mode: PaymentMode
    items: list[tuple[str, int]]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    hour: int
    minute: int
    credit: dict | None = None


@dataclass
class PlanCredit:
    code: str
    credit_id: UUID
    sale_code: str
    client_document: str
    original_amount: Decimal
    pending_amount: Decimal
    credit_date: date
    due_date: date
    status: CreditStatus
    risk: RiskLevel
    score: int
    recommended_limit: Decimal


@dataclass
class PlanPayment:
    code: str
    payment_id: UUID
    client_document: str
    amount: Decimal
    payment_date: date
    method: str
    reference: str | None
    remaining_balance: Decimal
    allocations: list[tuple[str, Decimal]]  # (credit_code, amount)


@dataclass
class Plan:
    sales: list[PlanSale]
    credits: list[PlanCredit]
    payments: list[PlanPayment]


def build_plan() -> Plan:
    prices = dict(MIGRATION_PRODUCT_PRICES)

    def amounts(items: list[tuple[str, int]]) -> tuple[Decimal, Decimal, Decimal, list]:
        subtotal = Decimal("0.00")
        lines = []
        for sku, qty in items:
            line = _money(prices[sku] * qty)
            lines.append((sku, qty, prices[sku], line))
            subtotal += line
        subtotal = _money(subtotal)
        tax = _money(subtotal * TAX_RATE)
        return subtotal, tax, subtotal + tax, lines

    raw: list[tuple[int, date, int, str | None, PaymentMode, list, dict | None]] = []
    for index, (sku, qty) in enumerate(CASH_LINES):
        day = SALES_FIRST_DATE + timedelta(
            days=round(index * (SALES_LAST_DATE - SALES_FIRST_DATE).days / (len(CASH_LINES) - 1))
        )
        items = [(sku, qty)]
        if index in CASH_SECOND_LINES:
            items.append(CASH_SECOND_LINES[index])
        raw.append((0, day, index, None, PaymentMode.CASH, items, None))
    for index, spec in enumerate(CREDIT_SALES):
        raw.append((0, spec["date"], len(CASH_LINES) + index, spec["client"],
                    PaymentMode.CREDIT, list(spec["items"]), spec))
    extra_offset = len(CASH_LINES) + len(CREDIT_SALES)
    for offset, spec in enumerate(EXTRA_CREDIT_SALES):
        raw.append((1, spec["date"], extra_offset + offset, spec["client"],
                    PaymentMode.CREDIT, list(spec["items"]), spec))
    extra_offset += len(EXTRA_CREDIT_SALES)
    # Newcomers always sort after all other records so base codes never change.
    for offset, spec in enumerate(NEW_CLIENT_CREDIT_SALES):
        raw.append((1, spec["date"], extra_offset + offset,
                    spec["client"], PaymentMode.CREDIT, list(spec["items"]), spec))
    raw.sort(key=lambda entry: (entry[0], entry[1], entry[2]))

    sales: list[PlanSale] = []
    credits: list[PlanCredit] = []
    for position, (_, day, _, client, mode, items, spec) in enumerate(raw, start=1):
        code = f"V-2026-{position:04d}"
        subtotal, tax, total, _ = amounts(items)
        sale = PlanSale(
            code=code,
            sale_id=_seed_id("sale", code),
            day=day,
            client_document=client,
            payment_mode=mode,
            items=items,
            subtotal=subtotal,
            tax=tax,
            total=total,
            hour=9 + (position * 7) % 11,
            minute=(position * 37) % 60,
        )
        sales.append(sale)
        if spec is not None:
            credit_code = f"F-2026-{len(credits) + 1:04d}"
            term = spec["term_days"] if spec["term_days"] is not None else 1
            credits.append(PlanCredit(
                code=credit_code,
                credit_id=_seed_id("credit", credit_code),
                sale_code=code,
                client_document=spec["client"],
                original_amount=total,
                pending_amount=total,
                credit_date=day,
                due_date=day + timedelta(days=term),
                status=CreditStatus.CURRENT,
                risk=spec["risk"],
                score=spec["score"],
                recommended_limit=spec["limit"],
            ))
            sale.credit = spec

    credit_by_code = {credit.code: credit for credit in credits}
    sale_by_code = {sale.code: sale for sale in sales}

    payment_seed: list[tuple[date, int, str, Decimal | None]] = []
    for order, credit in enumerate(credits):
        for pay_date, pay_amount in sale_by_code[credit.sale_code].credit["payments"]:
            payment_seed.append((pay_date, order, credit.code, pay_amount))
    payment_seed.sort(key=lambda entry: (entry[0], entry[1]))
    base_payment_total = sum(
        1 for pay in payment_seed
        if credit_by_code[pay[2]].client_document not in NEWCOMER_DOCUMENTS
    )

    payments: list[PlanPayment] = []
    base_payment_seq = 0
    newcomer_payment_seq = 0
    pending = {credit.code: credit.original_amount for credit in credits}
    outstanding: dict[str, Decimal] = {}
    events: list[tuple[date, int, str, object]] = [
        (credit.credit_date, 0, "credit", credit) for credit in credits
    ]
    events += [(pay[0], 1, "payment", pay) for pay in payment_seed]
    events.sort(key=lambda entry: (entry[0], entry[1]))

    for _, _, kind, payload in events:
        if kind == "credit":
            credit = payload
            outstanding[credit.client_document] = (
                outstanding.get(credit.client_document, Decimal("0.00")) + credit.original_amount
            )
            continue
        pay_date, _, credit_code, pay_amount = payload
        credit = credit_by_code[credit_code]
        applied = pending[credit_code] if pay_amount is None else pay_amount
        if applied <= Decimal("0.00") or applied > pending[credit_code]:
            raise ValueError(f"Payment for {credit_code} exceeds its pending balance")
        pending[credit_code] = _money(pending[credit_code] - applied)
        balance = _money(outstanding[credit.client_document] - applied)
        outstanding[credit.client_document] = balance
        # Base payments keep the numbering of the pre-newcomer seed exactly;
        # newcomer payments continue after all base payments so codes never
        # collide with records that already exist in a seeded demo database.
        if credit.client_document in NEWCOMER_DOCUMENTS:
            newcomer_payment_seq += 1
            sequence = base_payment_total + newcomer_payment_seq
        else:
            base_payment_seq += 1
            sequence = base_payment_seq
        code = f"P-2026-{sequence:04d}"
        method = PAYMENT_METHODS[sequence % len(PAYMENT_METHODS)]
        payments.append(PlanPayment(
            code=code,
            payment_id=_seed_id("payment", code),
            client_document=credit.client_document,
            amount=_money(applied),
            payment_date=pay_date,
            method=method,
            reference=None if method == "Efectivo" else f"OP-{sequence:06d}",
            remaining_balance=balance,
            allocations=[(credit_code, _money(applied))],
        ))

    for credit in credits:
        credit.pending_amount = pending[credit.code]
        if credit.pending_amount == Decimal("0.00"):
            credit.status = CreditStatus.PAID
        elif credit.due_date < REFERENCE_DATE:
            credit.status = CreditStatus.OVERDUE
        else:
            credit.status = CreditStatus.CURRENT

    return Plan(sales=sales, credits=credits, payments=payments)


async def _upsert_user(db) -> User:
    user = await db.scalar(select(User).where(User.email == "docente@example.com"))
    if user is None:
        user = User(
            id=_seed_id("user", "docente@example.com"),
            email="docente@example.com",
            full_name="Docente Baylon",
            hashed_password=hash_password(os.environ.get("DEMO_USER_PASSWORD", "DemoAPF2-2026!")),
            role=UserRole.OPERATOR,
            organization_id=DEFAULT_ORGANIZATION_ID,
        )
        db.add(user)
    elif "demo" in user.full_name.lower():
        user.full_name = "Docente Baylon"
    return user


async def _upsert_settings(db) -> None:
    values = {
        "business_name": "Cervecería Baylón",
        "business_phone": "+51 900 000 100",
        "business_address": "Av. Baylón 1200, Ate, Lima",
        "default_credit_term_days": 1,
        "max_credit_amount": Decimal("200.00"),
    }
    policy = await db.get(BusinessSettings, SETTINGS_ID)
    if policy is None:
        db.add(BusinessSettings(id=SETTINGS_ID, organization_id=DEFAULT_ORGANIZATION_ID,
                                due_alerts_enabled=True, **values))
    else:
        for field, value in values.items():
            setattr(policy, field, value)


async def _ensure_client(db, spec) -> Client:
    document, first, last, business, phone, address = spec
    client = await db.scalar(select(Client).where(Client.document == document))
    if client is not None:
        return client
    client = Client(
        id=_seed_id("client", document),
        first_name=first, last_name=last, business_name=business,
        document=document, phone=phone, address=address,
        organization_id=DEFAULT_ORGANIZATION_ID, is_active=True,
    )
    db.add(client)
    return client


async def _ensure_products(db) -> dict[str, Product]:
    products: dict[str, Product] = {}
    for sku in MIGRATION_PRODUCT_PRICES:
        product = await db.scalar(select(Product).where(Product.sku == sku))
        if product is None:
            raise RuntimeError(f"Catalog product {sku} missing; run 'alembic upgrade head' first")
        products[sku] = product
    return products


async def _insert_plan(db, plan, user, clients, products, running_stock) -> None:
    for sale in plan.sales:
        client = clients[sale.client_document] if sale.client_document else None
        client_name = (
            client.business_name or f"{client.first_name} {client.last_name}"
            if client else None
        )
        sale_moment = _moment(sale.day, sale.hour, sale.minute)
        db.add(Sale(
            id=sale.sale_id, code=sale.code, payment_mode=sale.payment_mode,
            client_id=client.id if client else None, client_name=client_name,
            created_by_id=user.id, subtotal=sale.subtotal, tax=sale.tax,
            total=sale.total, created_at=sale_moment, updated_at=sale_moment,
        ))
    await db.flush()

    for sale in plan.sales:
        sale_moment = _moment(sale.day, sale.hour, sale.minute)
        for sku, qty in sale.items:
            product = products[sku]
            line_subtotal = _money(product.price * qty)
            running_stock[sku] -= qty
            if running_stock[sku] < 0:
                raise RuntimeError(f"Seeded sales exceed stock for {sku}")
            product.stock = running_stock[sku]
            db.add(SaleItem(
                id=_seed_id("saleitem", f"{sale.code}:{sku}"),
                sale_id=sale.sale_id, product_id=product.id,
                product_name=product.name, product_category=product.category,
                unit_price=product.price, quantity=qty, line_subtotal=line_subtotal,
            ))
            db.add(InventoryMovement(
                id=_seed_id("movement", f"sale:{sale.code}:{sku}"),
                product_id=product.id, movement_type=InventoryMovementType.SALE,
                quantity_delta=-qty, stock_after=running_stock[sku],
                reference_id=sale.sale_id, note=f"Sale {sale.code}",
                created_by_id=user.id, created_at=sale_moment, updated_at=sale_moment,
            ))

    sale_ids = {sale.code: sale.sale_id for sale in plan.sales}
    for credit in plan.credits:
        client = clients[credit.client_document]
        credit_moment = _moment(credit.credit_date, 12, 0)
        db.add(Credit(
            id=credit.credit_id, code=credit.code, client_id=client.id,
            sale_id=sale_ids[credit.sale_code], created_by_id=user.id,
            original_amount=credit.original_amount, pending_amount=credit.pending_amount,
            credit_date=credit.credit_date, due_date=credit.due_date,
            status=credit.status, risk=credit.risk, score=credit.score,
            recommended_limit=credit.recommended_limit,
            created_at=credit_moment, updated_at=credit_moment,
        ))
    await db.flush()

    credit_ids = {credit.code: credit.credit_id for credit in plan.credits}
    for payment in plan.payments:
        client = clients[payment.client_document]
        client_name = client.business_name or f"{client.first_name} {client.last_name}"
        payment_moment = _moment(payment.payment_date, 17, 0)
        db.add(Payment(
            id=payment.payment_id, code=payment.code, client_id=client.id,
            client_name=client_name, amount=payment.amount,
            payment_date=payment.payment_date, method=payment.method,
            reference=payment.reference, remaining_balance=payment.remaining_balance,
            registered_by_id=user.id, created_at=payment_moment, updated_at=payment_moment,
        ))
        await db.flush()
        for credit_code, amount in payment.allocations:
            db.add(PaymentAllocation(
                id=_seed_id("allocation", f"{payment.code}:{credit_code}"),
                payment_id=payment.payment_id, credit_id=credit_ids[credit_code],
                amount=amount,
            ))


async def _backfill_newcomers(db, plan, user, clients, products) -> int:
    newcomer_sales = [s for s in plan.sales if s.client_document in NEWCOMER_DOCUMENTS]
    if not newcomer_sales:
        return 0
    exists = await db.scalar(
        select(Sale.id).where(Sale.code == newcomer_sales[0].code).limit(1)
    )
    if exists is not None:
        return 0
    newcomer_credits = [c for c in plan.credits if c.client_document in NEWCOMER_DOCUMENTS]
    codes = {c.code for c in newcomer_credits}
    newcomer_payments = [
        p for p in plan.payments
        if any(code in codes for code, _ in p.allocations)
    ]
    sub_plan = Plan(sales=newcomer_sales, credits=newcomer_credits, payments=newcomer_payments)
    running_stock = {sku: products[sku].stock for sku in products}
    await _insert_plan(db, sub_plan, user, clients, products, running_stock)
    return len(newcomer_sales)


async def seed_demo() -> None:
    settings = get_settings()
    if (
        os.environ.get("DEMO_MODE") != "true"
        or make_url(settings.database_url).database != "credify_demo"
        or settings.environment != "staging"
    ):
        raise SystemExit("Demo seed refused: staging and credify_demo are required.")

    plan = build_plan()
    async with SessionFactory() as db:
        try:
            user = await _upsert_user(db)
            await _upsert_settings(db)
            products = await _ensure_products(db)
            marker = await db.scalar(
                select(Sale.id).where(Sale.code == MARKER_SALE_CODE).limit(1)
            )
            clients = {spec[0]: await _ensure_client(db, spec) for spec in CLIENT_SPECS}
            if marker is not None:
                created = await _backfill_newcomers(db, plan, user, clients, products)
                await db.commit()
                if created:
                    print(
                        "Demo already seeded; existing fictional records were kept; "
                        f"backfilled {created} newcomer sale(s) with their credits/payments."
                    )
                else:
                    print("Demo already seeded; existing fictional records were kept.")
                return

            running_stock = {sku: products[sku].stock for sku in products}

            # Piscano (P006) is pre-loaded by migration 0002 with stock 8, already
            # below its minimum_stock of 10, so the demo shows an at-risk product
            # without inventing a new SKU or changing migration data.
            db.add(InventoryMovement(
                id=_seed_id("movement", "adjustment:P006:merma"),
                product_id=products["P006"].id,
                movement_type=InventoryMovementType.ADJUSTMENT,
                quantity_delta=-1,
                stock_after=running_stock["P006"] - 1,
                note="Merma: botella danada en almacen",
                created_by_id=user.id,
                created_at=_moment(date(2026, 10, 19), 18, 30),
                updated_at=_moment(date(2026, 10, 19), 18, 30),
            ))
            running_stock["P006"] -= 1
            replenishment = {
                "P001": 24, "P002": 19, "P003": 43, "P004": 7,
                "P005": 2, "P006": 1, "P007": 1, "P009": 64, "P010": 4,
            }
            for sku, quantity in replenishment.items():
                running_stock[sku] += quantity
                product = products[sku]
                product.stock = running_stock[sku]
                db.add(InventoryMovement(
                    id=_seed_id("movement", f"entry:{sku}"),
                    product_id=products[sku].id,
                    movement_type=InventoryMovementType.ENTRY,
                    quantity_delta=quantity, stock_after=running_stock[sku],
                    note="Ingreso de mercaderia para campaña ficticia",
                    created_by_id=user.id,
                    created_at=_moment(date(2026, 10, 20), 8, 0),
                    updated_at=_moment(date(2026, 10, 20), 8, 0),
                ))
            await _insert_plan(db, plan, user, clients, products, running_stock)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    totals = {
        "clients": len(CLIENT_SPECS),
        "products": len(MIGRATION_PRODUCT_PRICES),
        "sales": len(plan.sales),
        "credit_sales": len(plan.credits),
        "payments": len(plan.payments),
    }
    print(
        "Fictional Cerveceria Baylon demo ready: "
        + ", ".join(f"{value} {key}" for key, value in totals.items())
        + " (migration catalog P001-P010; no new products added). "
        + "All records are invented; no real personal data."
    )


if __name__ == "__main__":
    asyncio.run(seed_demo())
