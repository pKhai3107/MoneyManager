from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Category:
    id: Optional[int]
    key: str
    value: str
    type: int  # 0: chi, 1: thu

    @property
    def type_name(self) -> str:
        return "Thu nhập" if self.type == 1 else "Chi tiêu"

    @property
    def type_mark(self) -> str:
        return "+" if self.type == 1 else "-"

@dataclass
class Transaction:
    id: Optional[int]
    date: str
    amount: float
    category_id: int
    note: Optional[str] = None
    category_name: Optional[str] = None
    category_type: Optional[int] = None

    @classmethod
    def create_new(cls, amount: float, category_id: int, note: str = None) -> 'Transaction':
        return cls(
            id=None,
            date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            amount=amount,
            category_id=category_id,
            note=note
        )

    def is_income(self) -> bool:
        return self.amount > 0

    def is_expense(self) -> bool:
        return self.amount < 0
