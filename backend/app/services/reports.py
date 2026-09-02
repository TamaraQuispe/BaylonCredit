from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.commerce import Credit, CreditStatus
from app.schemas.reports import PortfolioClientReport, PortfolioReportRead, PortfolioSummary

DAYS_TO_ALERT = 5


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