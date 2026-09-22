from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_finance_role
from backend.app.models.schema import Transaction, User
from backend.app.services.report_export_service import ReportExportService


router = APIRouter(prefix="/api/reports", tags=["reports"])


def _period_start(period: str) -> tuple[date | None, str]:
    today = date.today()
    months = {"1m": 1, "3m": 3, "6m": 6, "all": None}
    if period not in months:
        raise HTTPException(status_code=422, detail="period must be 1m, 3m, 6m, or all")
    count = months[period]
    if count is None:
        return None, "All transactions"
    month_index = today.year * 12 + today.month - count
    start = date(month_index // 12, month_index % 12 + 1, 1)
    return start, f"{start.isoformat()} to {today.isoformat()}"


def _transactions(db: Session, user_id: str, period: str):
    start, label = _period_start(period)
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if start:
        query = query.filter(Transaction.date >= start, Transaction.date <= date.today())
    return query.order_by(Transaction.date.desc(), Transaction.id.desc()).all(), label


@router.get("/export/{file_format}")
def export_report(
    file_format: str,
    period: str = "6m",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_finance_role),
):
    transactions, period_label = _transactions(db, current_user.id, period)
    stamp = date.today().isoformat()
    if file_format == "pdf":
        content = ReportExportService.build_pdf(transactions, period_label)
        media_type = "application/pdf"
        filename = f"vyapar-sathi-report-{stamp}.pdf"
    elif file_format in {"xlsx", "excel"}:
        content = ReportExportService.build_excel(transactions, period_label)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"vyapar-sathi-report-{stamp}.xlsx"
    else:
        raise HTTPException(status_code=422, detail="format must be pdf or xlsx")

    return StreamingResponse(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
