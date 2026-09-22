from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_finance_role
from backend.app.models.schema import MonthlyBudget, User
from backend.app.schemas.schemas import BudgetUpsert
from backend.app.services.budget_service import BudgetService


router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("")
def list_budgets(
    month: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_finance_role),
):
    try:
        data = BudgetService.statuses(db, current_user.id, month)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="month must use YYYY-MM format") from exc
    return {"success": True, "data": data}


@router.post("")
def set_budget(
    payload: BudgetUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_finance_role),
):
    budget = BudgetService.upsert(
        db,
        current_user.id,
        payload.amount,
        payload.category,
        payload.month,
        payload.warning_threshold,
    )
    status = next(
        item
        for item in BudgetService.statuses(db, current_user.id, budget.year_month)
        if item["id"] == budget.id
    )
    return {"success": True, "data": status}


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_finance_role),
):
    budget = db.query(MonthlyBudget).filter(
        MonthlyBudget.id == budget_id,
        MonthlyBudget.user_id == current_user.id,
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(budget)
    db.commit()
    return {"success": True}
