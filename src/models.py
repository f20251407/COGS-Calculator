from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, validator
from typing import Optional


class FinancialState(BaseModel):
    opening_inventory: Decimal
    closing_inventory: Decimal
    cwip_opening: Decimal
    cwip_closing: Decimal
    cost_of_revenue: Decimal

    @validator("opening_inventory", "closing_inventory", "cwip_opening", "cwip_closing", "cost_of_revenue", pre=True)
    def to_decimal(cls, v):
        if v is None:
            return Decimal("0")
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except (InvalidOperation, ValueError):
            raise ValueError("Value must be coercible to Decimal")
