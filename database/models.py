from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


@dataclass
class User:
    user_id: int
    username: Optional[str]
    full_name: Optional[str]
    balance: Decimal
    referral_code: str
    referred_by: Optional[int]
    created_at: datetime
    is_admin: bool
    usdt_address: Optional[str]

    @classmethod
    def from_row(cls, row):
        return cls(
            user_id=row['user_id'],
            username=row['username'],
            full_name=row['full_name'],
            balance=row['balance'],
            referral_code=row['referral_code'],
            referred_by=row['referred_by'],
            created_at=row['created_at'],
            is_admin=row['is_admin'],
            usdt_address=row['usdt_address']
        )


@dataclass
class Deposit:
    deposit_id: int
    user_id: int
    amount: Decimal
    interest_rate: Decimal
    current_balance: Decimal
    status: str
    created_at: datetime
    last_accrual_date: Optional[date]
    total_earned: Decimal

    @classmethod
    def from_row(cls, row):
        return cls(
            deposit_id=row['deposit_id'],
            user_id=row['user_id'],
            amount=row['amount'],
            interest_rate=row['interest_rate'],
            current_balance=row['current_balance'],
            status=row['status'],
            created_at=row['created_at'],
            last_accrual_date=row['last_accrual_date'],
            total_earned=row['total_earned']
        )


@dataclass
class Transaction:
    transaction_id: int
    user_id: int
    transaction_type: str
    amount: Decimal
    status: str
    description: Optional[str]
    created_at: datetime
    deposit_id: Optional[int]
    admin_id: Optional[int]

    @classmethod
    def from_row(cls, row):
        return cls(
            transaction_id=row['transaction_id'],
            user_id=row['user_id'],
            transaction_type=row['transaction_type'],
            amount=row['amount'],
            status=row['status'],
            description=row['description'],
            created_at=row['created_at'],
            deposit_id=row['deposit_id'],
            admin_id=row['admin_id']
        )
