from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


TransactionType = Literal["income", "expense"]
WarningLevel = Literal["info", "warning", "danger"]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: TransactionType


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: TransactionType
    created_at: datetime


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    type: TransactionType
    category_id: int | None = None
    note: str | None = None
    occurred_at: datetime | None = None


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: float
    type: TransactionType
    category_id: int | None
    note: str | None
    occurred_at: datetime
    created_at: datetime


class TransactionSummary(BaseModel):
    income: float
    expense: float
    balance: float
    transaction_count: int


class PredictionCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    predicted_income: float = 0
    predicted_expense: float = 0
    predicted_balance: float = 0
    model_name: str | None = None
    raw_result: str | None = None


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_start: datetime
    period_end: datetime
    predicted_income: float
    predicted_expense: float
    predicted_balance: float
    model_name: str | None
    raw_result: str | None
    created_at: datetime


class WarningCreate(BaseModel):
    level: WarningLevel = "warning"
    title: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1)


class WarningRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: WarningLevel
    title: str
    message: str
    is_read: bool
    created_at: datetime
