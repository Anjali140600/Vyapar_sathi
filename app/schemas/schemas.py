from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict, Any
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

    @field_validator("date", mode="before")
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

class DashboardSummary(BaseModel):
    totalSales: float
    totalExpenses: float = 0
    profit: float
    gstTracked: float = 0

class HealthResponse(BaseModel):
    success: bool = True
    message: str
