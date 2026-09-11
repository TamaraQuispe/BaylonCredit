from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.commerce import Credit, CreditEvaluation, CreditStatus, RiskLevel
from app.models.settings import SETTINGS_ID, BusinessSettings
from app.schemas.reports import (
    ClientRiskReport,
    PortfolioClientReport,
    PortfolioReportRead,
    PortfolioSummary,
    RiskReportRead,
)

DAYS_TO_ALERT = 5

_RISK_ORDER = {
    RiskLevel.VERY_LOW: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


async def _sum_pending(db: AsyncSession, clause) -> float:
    value = await db.scalar(select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(clause))
    return float(value or 0)


async def build_portfolio_report(db: AsyncSession) -> PortfolioReportRead:
    overdue_condition = and_(
    Credit.pending_amount > 0, Credit.due_date < date.today()
)

    client_rows = (
        await db.execute(
            select(
                Client.id,
                Client.first_name,
                Client.last_name,
                Client.business_name,
                func.coalesce(func.sum(Credit.pending_amount), 0),
                func.coalesce(
                    func.sum(
                        case(
                            (overdue_condition, Credit.pending_amount),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.count(Credit.id),
                func.coalesce(
                    func.sum(
                        case((overdue_condition, 1), else_=0)
                    ),
                    0,
                ),
                func.min(Credit.due_date),
            )
            .join(Credit, Credit.client_id == Client.id)
            .where(Credit.status != CreditStatus.PAID)
            .group_by(Client.id)
            .order_by(func.sum(Credit.pending_amount).desc())
        )
    ).all()

    clients: list[PortfolioClientReport] = []
    total_pending = Decimal("0")
    total_overdue = Decimal("0")
    active_credits = 0
    overdue_credits = 0
    for row in client_rows:
        pending = Decimal(row[4] or 0)
        overdue = Decimal(row[5] or 0)
        total_pending += pending
        total_overdue += overdue
        active_credits += int(row[6] or 0)
        overdue_credits += int(row[7] or 0)
        clients.append(
            PortfolioClientReport(
                client_id=row[0],
                client_name=f"{row[1]} {row[2]}".strip(),
                business_name=row[3],
                total_pending=pending,
                total_overdue=overdue,
                active_credits=int(row[6] or 0),
                overdue_credits=int(row[7] or 0),
                earliest_due=row[8],
            )
        )

    paid_credits = await db.scalar(
        select(func.count(Credit.id)).where(Credit.status == CreditStatus.PAID)
    )
    due_soon_credits = await db.scalar(
        select(func.count(Credit.id)).where(
            Credit.status == CreditStatus.CURRENT,
            Credit.pending_amount > 0,
            Credit.due_date <= date.today() + timedelta(days=DAYS_TO_ALERT),
            Credit.due_date >= date.today(),
        )
    )
    total_recovered = await _sum_pending(
        db, Credit.status == CreditStatus.PAID
    )

    gross_issued = Decimal(
        await _sum_pending(db, Credit.status != CreditStatus.PAID)
    ) + Decimal(total_recovered)
    delinquency_rate = (
        (float(total_overdue) / float(gross_issued) * 100)
        if total_overdue and gross_issued
        else 0.0
    )

    return PortfolioReportRead(
        summary=PortfolioSummary(
            total_pending=total_pending,
            total_overdue=total_overdue,
            total_recovered=Decimal(total_recovered),
            delinquency_rate=round(delinquency_rate, 2),
            active_credits=active_credits,
            overdue_credits=overdue_credits,
            due_soon_credits=int(due_soon_credits or 0),
            paid_credits=int(paid_credits or 0),
            generated_at=date.today(),
        ),
        clients=clients,
    )


async def _max_overdue_days(db: AsyncSession, client_id) -> int:
    due_dates = list(
        await db.scalars(
            select(Credit.due_date).where(
                Credit.client_id == client_id,
                Credit.pending_amount > 0,
                Credit.due_date < date.today(),
            )
        )
    )
    if not due_dates:
        return 0
    return max((date.today() - due).days for due in due_dates)


async def build_risk_report(db: AsyncSession) -> RiskReportRead:
    settings = await db.get(BusinessSettings, SETTINGS_ID)
    default_line = settings.max_credit_amount if settings else Decimal("200")
    clients = list(
        await db.scalars(select(Client).where(Client.is_active.is_(True)))
    )
    reports: list[ClientRiskReport] = []
    for client in clients:
        latest = await db.scalar(
            select(CreditEvaluation)
            .where(CreditEvaluation.client_id == client.id)
            .order_by(CreditEvaluation.created_at.desc())
            .limit(1)
        )
        if latest is None:
            has_credits = await db.scalar(
                select(func.count(Credit.id)).where(Credit.client_id == client.id)
            )
            if not has_credits:
                continue
        client_name = client.business_name or f"{client.first_name} {client.last_name}"
        used = Decimal(
            await db.scalar(
                select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
                    Credit.client_id == client.id, Credit.pending_amount > 0
                )
            )
            or 0
        )
        assigned_line = latest.recommended_limit if latest else default_line
        available = max(Decimal("0"), assigned_line - used)
        utilization = float(used / assigned_line * 100) if assigned_line else 0.0
        overdue_amount = Decimal(
            await db.scalar(
                select(func.coalesce(func.sum(Credit.pending_amount), 0)).where(
                    Credit.client_id == client.id,
                    Credit.pending_amount > 0,
                    Credit.due_date < date.today(),
                )
            )
            or 0
        )
        overdue_credits = int(
            await db.scalar(
                select(func.count(Credit.id)).where(
                    Credit.client_id == client.id,
                    Credit.pending_amount > 0,
                    Credit.due_date < date.today(),
                )
            )
            or 0
        )
        next_due_date = await db.scalar(
            select(func.min(Credit.due_date)).where(
                Credit.client_id == client.id,
                Credit.pending_amount > 0,
                Credit.due_date >= date.today(),
            )
        )
        reports.append(
            ClientRiskReport(
                client_id=client.id,
                client_name=client_name,
                business_name=client.business_name,
                phone=client.phone,
                score=latest.score if latest else None,
                risk=latest.risk if latest else None,
                last_evaluation_at=latest.created_at if latest else None,
                recommendation=latest.recommendation if latest else None,
                assigned_line=assigned_line,
                used=used,
                available=available,
                utilization_percent=round(utilization, 2),
                pending_amount=used,
                overdue_amount=overdue_amount,
                overdue_credits=overdue_credits,
                max_overdue_days=await _max_overdue_days(db, client.id),
                next_due_date=next_due_date,
            )
        )

    def sort_key(report: ClientRiskReport) -> tuple[int, str]:
        risk = report.risk
        severity = _RISK_ORDER.get(risk, -1) if risk is not None else -1
        return (severity, str(-report.pending_amount))

    reports.sort(key=sort_key, reverse=True)
    return RiskReportRead(generated_at=date.today(), clients=reports)