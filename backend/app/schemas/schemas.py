from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import date as DateType, datetime

class UserBase(BaseModel):
    email: EmailStr
    fullName: str

class UserCreate(UserBase):
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    success: bool = True

    class Config:
        from_attributes = True

class Token(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    success: bool = True
    role: Literal["owner", "staff", "accountant"]


class CurrentUserResponse(BaseModel):
    id: str
    email: EmailStr
    fullName: str
    role: Literal["owner", "staff", "accountant"]
    success: bool = True

class ChatRequest(BaseModel):
    sessionId: Optional[str] = None
    message: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]

class TransactionBase(BaseModel):
    amount: float
    category: str
    type: Optional[str] = "expense"
    quantity: Optional[float] = None
    gst_amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[DateType] = None
    amount_paid: Optional[float] = None
    due_date: Optional[DateType] = None
    is_recurring: bool = False
    frequency: Optional[Literal["weekly", "monthly", "yearly"]] = None
    next_run_date: Optional[DateType] = None

    @field_validator("date", "due_date", "next_run_date", mode="before")
    @classmethod
    def normalize_date(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, DateType):
            return value
        if isinstance(value, datetime):
            return value.date()

        text = str(value).strip()
        if not text:
            return None

        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%m/%d/%Y",
            "%m-%d-%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue

        return value

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(TransactionBase):
    pass

class TransactionResponse(BaseModel):
    success: bool = True
    data: List[Dict[str, Any]] = []

class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)


class BudgetUpsert(BaseModel):
    amount: float = Field(gt=0)
    category: Optional[str] = None
    month: Optional[str] = None
    warning_threshold: float = Field(default=80, ge=1, le=100)

    @field_validator("month")
    @classmethod
    def validate_month(cls, value):
        if value in (None, ""):
            return None
        try:
            datetime.strptime(value, "%Y-%m")
        except ValueError as exc:
            raise ValueError("month must use YYYY-MM format") from exc
        return value

class DashboardSummary(BaseModel):
    totalSales: float
    totalExpenses: float = 0
    profit: float
    gstTracked: float = 0
    outstandingReceivables: float = 0
    outstandingPayables: float = 0

class HealthResponse(BaseModel):
    success: bool = True
    message: str
