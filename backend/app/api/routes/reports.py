from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reports import PortfolioReportRead
from app.services.reports import build_portfolio_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/portfolio", response_model=PortfolioReportRead)
async def portfolio_report(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioReportRead:
    return await build_portfolio_report(db)