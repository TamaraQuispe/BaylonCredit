"""Guardrails for the fictional Cerveceria Baylon demo seed.

Unit tests run without a database. Integration tests exercise the seed against a
real, throwaway PostgreSQL database and are skipped unless
``SEED_DEMO_TEST_DATABASE_URL`` points at an empty database named
``credify_demo`` (for example one created with ``docker run postgres:17-alpine``
that has just been migrated with ``alembic upgrade head``). They never touch a
shared or production database: the seed itself refuses to run outside staging
on a database not named ``credify_demo``.

The seed reuses the ten catalog products pre-loaded by migration
``20260901_0002_commerce`` (P001-P010); it must never invent products, SKUs or
categories of its own.
"""

import inspect
import os
import re
from collections import Counter
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.scripts import seed_demo

PLAN = seed_demo.build_plan()
FORBIDDEN_TOKENS = ("demo", "demonstracion", "demostración", "ficticio", "prueba", "dummy", "lorem")
MIGRATION_SKUS = tuple(seed_demo.MIGRATION_PRODUCT_PRICES)
# Assembled at runtime so this file does not hard-code the invented brand tokens.
INVENTED_BRAND_TOKENS = ("BA" + "YA", "Baylon" + " Amber")


def test_plan_volume_and_variety() -> None:
    assert len(PLAN.sales) >= 60
    assert len(PLAN.credits) >= 24
    assert len(PLAN.payments) >= 15
    assert len(seed_demo.CLIENT_SPECS) == 50
    assert len(MIGRATION_SKUS) == 10
    modes = Counter(sale.payment_mode for sale in PLAN.sales)
    assert modes[seed_demo.PaymentMode.CASH] > 0
    assert modes[seed_demo.PaymentMode.CREDIT] > 0


def test_seed_source_has_no_invented_brand() -> None:
    source = inspect.getsource(seed_demo)
    for token in INVENTED_BRAND_TOKENS:
        assert token not in source


def test_every_seeded_product_reference_exists_in_migration() -> None:
    catalog = set(MIGRATION_SKUS)
    assert catalog == {"P001", "P002", "P003", "P004", "P005",
                       "P006", "P007", "P008", "P009", "P010"}
    for sale in PLAN.sales:
        for sku, qty in sale.items:
            assert sku in catalog, sku
            assert qty > 0
    # Raw line definitions must not reference anything outside the migration catalog.
    for sku, _ in seed_demo.CASH_LINES:
        assert sku in catalog, sku
    for sku, _ in seed_demo.CASH_SECOND_LINES.values():
        assert sku in catalog, sku
    for spec in seed_demo.CREDIT_SALES:
        for sku, _ in spec["items"]:
            assert sku in catalog, sku


def test_no_demo_or_dummy_wording_anywhere() -> None:
    names = [spec[1] + " " + spec[2] + " " + (spec[3] or "") for spec in seed_demo.CLIENT_SPECS]
    catalog = " ".join(names).lower()
    for token in FORBIDDEN_TOKENS:
        assert token not in catalog


def test_client_identities_are_fake_but_plausible() -> None:
    documents = [spec[0] for spec in seed_demo.CLIENT_SPECS]
    assert len(documents) == len(set(documents))
    for document in documents:
        assert re.fullmatch(r"9\d{7}", document), document
    for spec in seed_demo.CLIENT_SPECS:
        assert re.fullmatch(r"\+51 900 000 \d{3}", spec[4]), spec[4]
        assert re.search(r"\d", spec[5])  # has a street number like a real address


def test_newcomer_clients_are_appended_after_the_base_roster() -> None:
    documents = [spec[0] for spec in seed_demo.CLIENT_SPECS]
    assert documents[:24] == [f"900000{n:02d}" for n in range(1, 25)]
    assert documents[24:28] == ["90000025", "90000026", "90000027", "90000028"]
    assert documents[28:] == [str(90000029 + n) for n in range(22)]
    assert seed_demo.NEWCOMER_DOCUMENTS == frozenset(documents[24:])


def test_newcomer_records_continue_base_code_sequences() -> None:
    # The four newcomers must extend, never renumber, the base records.
    sales = [s.code for s in PLAN.sales]
    assert sales[:64] == [f"V-2026-{n:04d}" for n in range(1, 65)]
    assert sales[64:] == [f"V-2026-{n:04d}" for n in range(65, 91)]
    codes = [c.code for c in PLAN.credits]
    assert codes == [f"F-2026-{n:04d}" for n in range(1, 55)]
    # Payments are ordered by event date; base ones keep P-2026-0001..0018
    # and the two newcomer payments continue with P-2026-0019..0020.
    payments = [p.code for p in PLAN.payments]
    assert len(set(payments)) == len(payments)
    assert sorted(payments) == [f"P-2026-{n:04d}" for n in range(1, 43)]
    newcomer_payments = sorted(
        p.code for p in PLAN.payments if p.client_document in seed_demo.NEWCOMER_DOCUMENTS
    )
    assert newcomer_payments == [f"P-2026-{n:04d}" for n in range(19, 43)]
    newcomers = {s.client_document for s in PLAN.sales[64:]}
    assert newcomers == seed_demo.NEWCOMER_DOCUMENTS


def test_sale_dates_are_fixed_within_the_demo_window() -> None:
    assert min(s.day for s in PLAN.sales) >= date(2026, 9, 2)
    assert max(s.day for s in PLAN.sales) <= date(2026, 10, 28)


def test_totals_are_consistent() -> None:
    for sale in PLAN.sales:
        assert sale.total == sale.subtotal + sale.tax
        assert sale.tax == (sale.subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
        assert sale.subtotal > 0


def test_credit_amounts_respect_the_business_cap() -> None:
    for credit in PLAN.credits:
        assert credit.original_amount <= Decimal("200.00")
        assert credit.recommended_limit <= Decimal("200.00")


def test_payment_allocations_never_exceed_credit() -> None:
    allocated = Counter()
    for payment in PLAN.payments:
        assert payment.amount > 0
        for credit_code, amount in payment.allocations:
            assert amount > 0
            allocated[credit_code] += amount
    by_code = {credit.code: credit for credit in PLAN.credits}
    for code, total in allocated.items():
        assert total <= by_code[code].original_amount


def test_credit_status_matches_amounts_and_reference_date() -> None:
    for credit in PLAN.credits:
        if credit.pending_amount == Decimal("0.00"):
            assert credit.status is seed_demo.CreditStatus.PAID
        elif credit.due_date < seed_demo.REFERENCE_DATE:
            assert credit.status is seed_demo.CreditStatus.OVERDUE
        else:
            assert credit.status is seed_demo.CreditStatus.CURRENT
        assert credit.pending_amount >= Decimal("0.00")


def test_reference_date_is_fixed() -> None:
    assert seed_demo.REFERENCE_DATE == date(2026, 11, 15)


def test_distribution_matches_expected_demo_shape() -> None:
    total = len(PLAN.credits)
    paid = sum(1 for c in PLAN.credits if c.status is seed_demo.CreditStatus.PAID)
    overdue = sum(1 for c in PLAN.credits if c.status is seed_demo.CreditStatus.OVERDUE)
    current = sum(1 for c in PLAN.credits if c.status is seed_demo.CreditStatus.CURRENT)
    assert 0.35 <= paid / total <= 0.60
    assert 0.30 <= overdue / total <= 0.55
    assert current / total <= 0.25
    assert paid > overdue
    # On-time and late payers, plus partial abonos on still-pending credit.
    paid_late = 0
    paid_on_time = 0
    partial = 0
    payments_by_credit: dict[str, list[date]] = {}
    for payment in PLAN.payments:
        for credit_code, _ in payment.allocations:
            payments_by_credit.setdefault(credit_code, []).append(payment.payment_date)
    for credit in PLAN.credits:
        dates = payments_by_credit.get(credit.code, [])
        if credit.status is seed_demo.CreditStatus.PAID and dates:
            (paid_late, paid_on_time) = (
                (paid_late + 1, paid_on_time)
                if max(dates) > credit.due_date
                else (paid_late, paid_on_time + 1)
            )
        if payments_by_credit.get(credit.code) and credit.pending_amount > 0:
            partial += 1
    assert paid_on_time >= 4
    assert paid_late >= 3
    assert partial >= 5
    assert sum(1 for c in PLAN.credits if c.status is seed_demo.CreditStatus.CURRENT) >= 4
    assert sum(1 for c in PLAN.credits if c.status is seed_demo.CreditStatus.OVERDUE) >= 10


def test_payment_dates_not_before_credit_dates() -> None:
    credit_dates = {credit.code: credit.credit_date for credit in PLAN.credits}
    for payment in PLAN.payments:
        for credit_code, _ in payment.allocations:
            assert payment.payment_date >= credit_dates[credit_code]


def test_plan_is_deterministic() -> None:
    again = seed_demo.build_plan()
    assert [s.code for s in PLAN.sales] == [s.code for s in again.sales]
    assert [c.code for c in PLAN.credits] == [c.code for c in again.credits]
    assert [p.code for p in PLAN.payments] == [p.code for p in again.payments]
    assert [s.sale_id for s in PLAN.sales] == [s.sale_id for s in again.sales]


def test_codes_are_unique() -> None:
    for codes in (
        [s.code for s in PLAN.sales],
        [c.code for c in PLAN.credits],
        [p.code for p in PLAN.payments],
    ):
        assert len(codes) == len(set(codes))


def test_credit_sales_reference_clients_and_cash_sales_do_not() -> None:
    for sale in PLAN.sales:
        if sale.payment_mode is seed_demo.PaymentMode.CREDIT:
            assert sale.client_document in {spec[0] for spec in seed_demo.CLIENT_SPECS}
        else:
            assert sale.client_document is None


def test_outstanding_is_below_caps() -> None:
    by_client: dict[str, Decimal] = {}
    for credit in PLAN.credits:
        by_client[credit.client_document] = (
            by_client.get(credit.client_document, Decimal("0.00")) + credit.pending_amount
        )
    # No client is seeded with more pending than the per-credit cap times three.
    assert all(value <= Decimal("600.00") for value in by_client.values())


def test_no_credit_evaluation_rows_are_planned() -> None:
    assert not hasattr(seed_demo, "CreditEvaluation")


TEST_DATABASE_URL = os.environ.get("SEED_DEMO_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="SEED_DEMO_TEST_DATABASE_URL not set (needs a migrated, empty credify_demo database)",
)


@pytest.fixture
async def harness():
    if not TEST_DATABASE_URL:
        pytest.skip("SEED_DEMO_TEST_DATABASE_URL not set")
    engine = create_async_engine(TEST_DATABASE_URL)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setattr(
        seed_demo, "SessionFactory", async_sessionmaker(engine, expire_on_commit=False)
    )
    monkeypatch.setattr(
        seed_demo,
        "get_settings",
        lambda: SimpleNamespace(database_url=TEST_DATABASE_URL, environment="staging"),
    )
    yield SimpleNamespace(engine=engine)
    monkeypatch.undo()
    await engine.dispose()


@needs_db
async def test_seed_is_idempotent(harness) -> None:
    await seed_demo.seed_demo()
    counts_before = {}
    async with harness.engine.connect() as conn:
        for table in ("clients", "products", "sales", "sale_items", "credits",
                      "payments", "payment_allocations", "inventory_movements"):
            counts_before[table] = (
                await conn.execute(text(f"SELECT count(*) FROM {table}"))
            ).scalar_one()
    await seed_demo.seed_demo()
    async with harness.engine.connect() as conn:
        for table, expected in counts_before.items():
            count = (
                await conn.execute(text(f"SELECT count(*) FROM {table}"))
            ).scalar_one()
            assert count == expected, f"{table} changed after reseeding"


@needs_db
async def test_seed_dataset_invariants(harness) -> None:
    async with harness.engine.connect() as conn:
        counts = {}
        for table in ("clients", "products", "sales", "credits", "payments"):
            counts[table] = (
                await conn.execute(text(f"SELECT count(*) FROM {table}"))
            ).scalar_one()
        assert counts["clients"] == 50
        assert counts["products"] == 10
        assert counts["sales"] == 90
        assert counts["credits"] == 54
        assert counts["payments"] == 42
        debt_clients = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM clients WHERE document IN "
                    "('90000029', '90000030', '90000031', '90000032', '90000033', "
                    "'90000034', '90000035', '90000036', '90000037', '90000038')"
                )
            )
        ).scalar_one()
        assert debt_clients == 10

        # Statuses agree with amounts.
        mismatched = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM credits WHERE "
                    "(pending_amount = 0 AND status != 'PAID') OR "
                    "(pending_amount > 0 AND status = 'PAID') OR "
                    "(pending_amount > 0 AND due_date < :ref AND status = 'CURRENT') OR "
                    "(pending_amount > 0 AND due_date >= :ref AND status = 'OVERDUE')"
                ),
                {"ref": seed_demo.REFERENCE_DATE},
            )
        ).scalar_one()
        assert mismatched == 0

        # Payment allocations sum to the payment amount...
        bad_payment = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM ("
                    "  SELECT p.id FROM payments p JOIN payment_allocations a "
                    "  ON a.payment_id = p.id GROUP BY p.id, p.amount "
                    "  HAVING sum(a.amount) != p.amount) x"
                )
            )
        ).scalar_one()
        assert bad_payment == 0

        # ...and never pay more than the credit originally granted, nor its pending part.
        bad_credit = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM credits c WHERE EXISTS ("
                    "  SELECT 1 FROM payment_allocations a WHERE a.credit_id = c.id "
                    "  GROUP BY a.credit_id "
                    "  HAVING sum(a.amount) != c.original_amount - c.pending_amount)"
                )
            )
        ).scalar_one()
        assert bad_credit == 0

        # Orphaned foreign keys.
        orphans = (
            await conn.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM sale_items si "
                    " LEFT JOIN products p ON p.id = si.product_id WHERE p.id IS NULL) + "
                    "(SELECT count(*) FROM credits c "
                    " LEFT JOIN sales s ON s.id = c.sale_id WHERE s.id IS NULL) + "
                    "(SELECT count(*) FROM credits c "
                    " LEFT JOIN clients cl ON cl.id = c.client_id WHERE cl.id IS NULL) + "
                    "(SELECT count(*) FROM payment_allocations a "
                    " LEFT JOIN credits c ON c.id = a.credit_id WHERE c.id IS NULL)"
                )
            )
        ).scalar_one()
        assert orphans == 0

        # Every product has non-negative stock.
        negative = (
            await conn.execute(text("SELECT count(*) FROM products WHERE stock < 0"))
        ).scalar_one()
        assert negative == 0
        # The seed must not have invented products, SKUs or categories.
        skus = (
            await conn.execute(text("SELECT array_agg(DISTINCT sku ORDER BY sku) FROM products"))
        ).scalar_one()
        assert list(skus) == sorted(MIGRATION_SKUS)

        # Every sold line points at a migration catalog product.
        unknown = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM sale_items si JOIN products p ON p.id = si.product_id "
                    "WHERE p.sku NOT IN :skus"
                ).bindparams(bindparam("skus", expanding=True)),
                {"skus": list(MIGRATION_SKUS)},
            )
        ).scalar_one()
        assert unknown == 0

        sold_mismatch = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM products p WHERE coalesce(("
                    "  SELECT sum(si.quantity) FROM sale_items si"
                    " WHERE si.product_id = p.id), 0) != "
                    "-coalesce((SELECT sum(m.quantity_delta) FROM inventory_movements m "
                    "WHERE m.product_id = p.id AND m.movement_type = 'SALE'), 0)"
                )
            )
        ).scalar_one()
        assert sold_mismatch == 0

        # Demo data never looks like real personal data or ML labels.
        leaks = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM clients WHERE "
                    "lower(first_name || ' ' || last_name || ' ' "
                    "|| coalesce(business_name, '')) LIKE '%demo%'"
                )
            )
        ).scalar_one()
        assert leaks == 0
        evaluations = (
            await conn.execute(text("SELECT count(*) FROM credit_evaluations"))
        ).scalar_one()
        assert evaluations == 0

        # Singles: one docente, one settings row with the generic name.
        assert (
            await conn.execute(
                text("SELECT count(*) FROM users WHERE email = 'docente@example.com'")
            )
        ).scalar_one() == 1
        settings_name = (
            await conn.execute(text("SELECT business_name FROM business_settings LIMIT 1"))
        ).scalar_one()
        assert "DEMO" not in settings_name.upper()
