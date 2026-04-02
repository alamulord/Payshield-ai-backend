# app/schemas/transaction.py — Pydantic schemas for transactions
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TransactionBase(BaseModel):
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD", max_length=10)
    merchant_name: str = Field(..., max_length=255)
    merchant_category: Optional[str] = None
    payment_method: str = Field(..., description="visa, mastercard, paypal, amex")
    card_last4: Optional[str] = Field(None, max_length=4)
    country: str = Field(..., max_length=5)
    ip_address: Optional[str] = None
    device: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction via POST"""
    pass


class TransactionResponse(BaseModel):
    id: str
    tx_id: str
    amount: float
    currency: str
    merchant_name: str
    merchant_category: Optional[str] = None
    merchant_icon: str = "store"
    payment_method: str
    card_last4: Optional[str] = None
    country: str
    country_name: Optional[str] = None
    ip_address: Optional[str] = None
    device: Optional[str] = None
    risk_score: float
    risk_level: str
    risk_factors: Optional[str] = None
    status: str
    status_color: str
    timestamp: datetime
    processed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionFilter(BaseModel):
    status: Optional[str] = None
    risk_level: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    merchant: Optional[str] = None
    country: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
