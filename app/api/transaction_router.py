from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date as date_type
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.data_service import DataService
from app.models.schema import Transaction, User
from app.schemas.schemas import TransactionCreate, TransactionUpdate, TransactionResponse, DashboardSummary
from typing import List

router = APIRouter(prefix="/api", tags=["transactions"])

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
    current_user: User = Depends(get_current_user),
):
    new_tx = Transaction(
        user_id=current_user.id,
        amount=item.amount,
        quantity=item.quantity,
        category=item.category,
        type=item.type,
        gst_amount=item.gst_amount,
        description=item.description,
        date=item.date or date_type.today()
    )
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)
    return {"success": True, "data": [{"id": str(new_tx.id), "amount": str(new_tx.amount)}]}

@router.get("/transactions", response_model=TransactionResponse)
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txs = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.created_at.desc()).all()
    return {
        "success": True, 
        "data": [
            {
                "id": t.id,
                "amount": float(t.amount), 
                "quantity": float(t.quantity) if t.quantity else 0,
                "category": t.category, 
                "transaction_type": t.type, 
                "gst_amount": float(t.gst_amount) if t.gst_amount else 0,
                "description": t.description,
                "transaction_date": str(t.date)
            } for t in txs
        ]
    }

@router.put("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    item: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.amount = item.amount
    tx.quantity = item.quantity
    tx.category = item.category
    tx.type = item.type
    tx.gst_amount = item.gst_amount
    tx.description = item.description
    tx.date = item.date or tx.date or date_type.today()

    db.commit()
    db.refresh(tx)
    return {"success": True, "data": [{"id": str(tx.id), "amount": str(tx.amount)}]}

@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    # using DataService logic
    service = DataService()
    summary = service.get_current_month_summary(db, user_id=current_user.id)
    gst_total = db.query(func.sum(Transaction.gst_amount)).filter(
        Transaction.user_id == current_user.id
    ).scalar() or 0
    return {
        "totalSales": summary["income"],
        "totalExpenses": summary["expense"],
        "profit": summary["profit"],
        "gstTracked": float(gst_total),
    }

@router.get("/health")
def health_check():
    return {"success": True, "message": "Vyapar Sathi Backend is healthy"}
