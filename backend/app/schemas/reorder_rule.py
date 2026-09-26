from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator


class ReorderRuleCreate(BaseModel):
    product_id: int
    location_id: Optional[int] = None
    minimum_quantity: Decimal
    reorder_quantity: Decimal
    active: Optional[bool] = True

    @model_validator(mode="after")
    def validate_quantities(self) -> "ReorderRuleCreate":
        if self.minimum_quantity < Decimal("0"):
            raise ValueError("Minimum quantity cannot be negative.")
        if self.reorder_quantity <= Decimal("0"):
            raise ValueError("Reorder quantity must be greater than zero.")
        return self


class ReorderRuleUpdate(BaseModel):
    product_id: Optional[int] = None
    location_id: Optional[int] = None
    minimum_quantity: Optional[Decimal] = None
    reorder_quantity: Optional[Decimal] = None
    active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_quantities(self) -> "ReorderRuleUpdate":
        if self.minimum_quantity is not None and self.minimum_quantity < Decimal("0"):
            raise ValueError("Minimum quantity cannot be negative.")
        if self.reorder_quantity is not None and self.reorder_quantity <= Decimal("0"):
            raise ValueError("Reorder quantity must be greater than zero.")
        return self


class ReorderRuleResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    sku: Optional[str] = None
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    minimum_quantity: Decimal
    reorder_quantity: Decimal
    active: bool

    model_config = ConfigDict(from_attributes=True)
