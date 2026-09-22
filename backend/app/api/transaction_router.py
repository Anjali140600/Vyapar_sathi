from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date as date_type
from backend.app.core.database import get_db
from backend.app.core.security import (
    require_any_business_role,
    require_finance_role,
    require_owner,
)
from backend.app.services.data_service import DataService
from backend.app.services.payment_due_service import (
    PaymentDueService,
    calculate_payment_fields,
    due_direction,
)
from backend.app.services.recurring_transaction_service import (
    RecurringTransactionService,
    prepare_schedule,
)
from backend.app.models.schema import Transaction, User
from backend.app.schemas.schemas import DashboardSummary, PaymentCreate, TransactionCreate, TransactionUpdate, TransactionResponse
router = APIRouter(prefix="/api", tags=["transactions"])


def _serialize_transaction(transaction: Transaction) -> dict:
    return {
        "id": transaction.id,
        "amount": float(transaction.amount),
        "amount_paid": float(transaction.amount_paid or 0),
        "amount_due": float(transaction.amount_due or 0),
        "due_date": str(transaction.due_date) if transaction.due_date else None,
        "due_direction": due_direction(transaction.type),
        "quantity": float(transaction.quantity) if transaction.quantity else 0,
        "category": transaction.category,
        "transaction_type": transaction.type,
        "gst_amount": float(transaction.gst_amount) if transaction.gst_amount else 0,
        "description": transaction.description,
        "transaction_date": str(transaction.date),
        "is_recurring": bool(transaction.is_recurring),
        "frequency": transaction.frequency,
        "next_run_date": str(transaction.next_run_date) if transaction.next_run_date else None,
        "recurring_parent_id": transaction.recurring_parent_id,
    }

@router.get("/transaction-types")
def get_types():
    """Provides categories and flow for frontend dropdowns."""
    return {
        "success": True,
        "types": [
            {"value": "sales", "label": "Sales/Revenue", "flow": "in"},
            {"value": "service", "label": "Service Income", "flow": "in"},
            {"value": "purchase", "label": "Purchase/Inventory", "flow": "out"},
            {"value": "salary", "label": "Salary/Wages", "flow": "out"},
            {"value": "rent", "label": "Rent/Utilities", "flow": "out"},
            {"value": "gst_payment", "label": "GST Tax Payment", "flow": "out"},
            {"value": "other_income", "label": "Other Income", "flow": "in"},
            {"value": "other_expense", "label": "Other Expense", "flow": "out"}
        ]
    }

@router.post("/transactions", response_model=TransactionResponse)
def add_transaction(
    item: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_business_role),
):
    transaction_date = item.date or date_type.today()
    try:
        frequency, next_run_date = prepare_schedule(
            transaction_date,
            item.is_recurring,
            item.frequency,
            item.next_run_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        amount_paid, amount_due, due_date = calculate_payment_fields(
            item.amount,
            item.amount_paid,
            item.due_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    new_tx = Transaction(
        user_id=current_user.id,
        amount=item.amount,
        quantity=item.quantity,
        category=item.category,
        type=item.type,
        gst_amount=item.gst_amount,
        description=item.description,
        date=transaction_date,
        amount_paid=amount_paid,
        amount_due=amount_due,
        due_date=due_date,
        is_recurring=item.is_recurring,
        frequency=frequency,
        next_run_date=next_run_date,
    )
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)
    return {"success": True, "data": [{"id": str(new_tx.id), "amount": str(new_tx.amount)}]}

@router.get("/transactions", response_model=TransactionResponse)
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_business_role),
):
    RecurringTransactionService.generate_due(db, user_id=current_user.id)
    txs = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.created_at.desc()).all()
    return {
        "success": True,
        "data": [_serialize_transaction(transaction) for transaction in txs]
    }

@router.put("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    item: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_finance_role),
):
    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction_date = item.date or tx.date or date_type.today()
    try:
        frequency, next_run_date = prepare_schedule(
            transaction_date,
            item.is_recurring,
            item.frequency,
            item.next_run_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        amount_paid, amount_due, due_date = calculate_payment_fields(
            item.amount,
            item.amount_paid,
            item.due_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    tx.amount = item.amount
    tx.quantity = item.quantity
    tx.category = item.category
    tx.type = item.type
    tx.gst_amount = item.gst_amount
    tx.description = item.description
    tx.date = transaction_date
    tx.amount_paid = amount_paid
    tx.amount_due = amount_due
    tx.due_date = due_date
    tx.is_recurring = item.is_recurring
    tx.frequency = frequency
    tx.next_run_date = next_run_date

    db.commit()
    db.refresh(tx)
    return {"success": True, "data": [{"id": str(tx.id), "amount": str(tx.amount)}]}


@router.get("/dues")
def list_dues(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_business_role),
):
    due_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.amount_due > 0,
    ).order_by(Transaction.due_date.asc()).all()
    return {
        "success": True,
        "data": [_serialize_transaction(transaction) for transaction in due_transactions],
    }


@router.post("/transactions/{transaction_id}/payments")
def record_payment(
    transaction_id: int,
    payment: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_finance_role),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id,
    ).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    try:
        PaymentDueService.record_payment(transaction, payment.amount)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.commit()
    db.refresh(transaction)
    return {"success": True, "data": _serialize_transaction(transaction)}

@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(tx)
    db.commit()
    return {"success": True}

@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_business_role),
):
    RecurringTransactionService.generate_due(db, user_id=current_user.id)
    # using DataService logic
    service = DataService()
    summary = service.get_current_month_summary(db, user_id=current_user.id)
    gst_total = db.query(func.sum(Transaction.gst_amount)).filter(
        Transaction.user_id == current_user.id
    ).scalar() or 0
    outstanding = PaymentDueService.outstanding_totals(db, current_user.id)
    return {
        "totalSales": summary["income"],
        "totalExpenses": summary["expense"],
        "profit": summary["profit"],
        "gstTracked": float(gst_total),
        "outstandingReceivables": outstanding["receivables"],
        "outstandingPayables": outstanding["payables"],
    }

@router.get("/health")
def health_check():
    return {"success": True, "message": "Vyapar Sathi Backend is healthy"}
