"""Monthly overall and category expense budget calculations."""

from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.schema import MonthlyBudget, Transaction
from backend.app.services.data_service import DataService


OVERALL_CATEGORY = "__overall__"


class BudgetService:
    @staticmethod
    def normalize_month(value: str | None) -> str:
        return value or date.today().strftime("%Y-%m")

    @staticmethod
    def normalize_category(value: str | None) -> str:
        clean = " ".join((value or "").split()).strip()
        return clean[:50] if clean else OVERALL_CATEGORY

    @staticmethod
    def month_range(year_month: str) -> tuple[date, date]:
        year, month = (int(part) for part in year_month.split("-"))
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])

    @classmethod
    def upsert(
        cls,
        db: Session,
        user_id: str,
        amount: float,
        category: str | None = None,
        month: str | None = None,
        warning_threshold: float = 80,
    ) -> MonthlyBudget:
        year_month = cls.normalize_month(month)
        normalized_category = cls.normalize_category(category)
        budget = db.query(MonthlyBudget).filter(
            MonthlyBudget.user_id == user_id,
            MonthlyBudget.year_month == year_month,
            func.lower(MonthlyBudget.category) == normalized_category.lower(),
        ).first()
        if budget is None:
            budget = MonthlyBudget(
                user_id=user_id,
                year_month=year_month,
                category=normalized_category,
            )
            db.add(budget)
        budget.amount = Decimal(str(amount)).quantize(Decimal("0.01"))
        budget.warning_threshold = Decimal(str(warning_threshold)).quantize(
            Decimal("0.01")
        )
        db.commit()
        db.refresh(budget)
        return budget

    @classmethod
    def statuses(cls, db: Session, user_id: str, month: str | None = None) -> list[dict]:
        year_month = cls.normalize_month(month)
        start, end = cls.month_range(year_month)
        budgets = db.query(MonthlyBudget).filter(
            MonthlyBudget.user_id == user_id,
            MonthlyBudget.year_month == year_month,
        ).order_by(MonthlyBudget.category.asc()).all()

        expense_rows = db.query(
            Transaction.category, func.sum(Transaction.amount)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type.in_(DataService.EXPENSE_TYPES),
            Transaction.date >= start,
            Transaction.date <= end,
        ).group_by(Transaction.category).all()
        category_spend = {
            (category or "General").strip().lower(): float(total or 0)
            for category, total in expense_rows
        }
        total_spend = sum(category_spend.values())

        return [
            cls.serialize(
                budget,
                total_spend
                if budget.category == OVERALL_CATEGORY
                else category_spend.get(budget.category.lower(), 0.0),
            )
            for budget in budgets
        ]

    @staticmethod
    def serialize(budget: MonthlyBudget, spent: float = 0.0) -> dict:
        limit = float(budget.amount or 0)
        percentage = round((spent / limit * 100), 2) if limit else 0.0
        threshold = float(budget.warning_threshold or 80)
        if percentage >= 100:
            status = "exceeded"
        elif percentage >= threshold:
            status = "warning"
        else:
            status = "safe"
        return {
            "id": budget.id,
            "month": budget.year_month,
            "category": None if budget.category == OVERALL_CATEGORY else budget.category,
            "label": "Overall expenses" if budget.category == OVERALL_CATEGORY else budget.category,
            "amount": limit,
            "spent": round(float(spent), 2),
            "remaining": round(limit - float(spent), 2),
            "percentage": percentage,
            "warning_threshold": threshold,
            "status": status,
        }
