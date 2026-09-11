from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.reports import PortfolioReportRead, RiskReportRead
from app.services.reports import build_portfolio_report, build_risk_report

router = APIRouter(prefix="/reports", tags=["reports"])

can_view_reports = require_roles(
    UserRole.ADMIN, UserRole.VIEWER, UserRole.CREDIT, UserRole.COLLECTIONS
)


@router.get("/portfolio", response_model=PortfolioReportRead)
async def portfolio_report(
    _: User = Depends(can_view_reports),
    db: AsyncSession = Depends(get_db),
) -> PortfolioReportRead:
    return await build_portfolio_report(db)


@router.get("/risk", response_model=RiskReportRead)
async def risk_report(
    _: User = Depends(can_view_reports),
    db: AsyncSession = Depends(get_db),
) -> RiskReportRead:
    return await build_risk_report(db)