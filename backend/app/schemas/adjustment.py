from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import AdjustmentStatus


class AdjustmentCreate(BaseModel):
    product_id: int
    location_id: int
    counted_quantity: Decimal
    reason: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_counted_quantity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            qty_raw = data.get("counted_quantity")
            if qty_raw is not None:
                try:
                    qty = Decimal(str(qty_raw))
                    if qty < Decimal("0"):
                        raise ValueError("Counted quantity cannot be negative.")
                    data["counted_quantity"] = qty
                except (ValueError, TypeError) as e:
                    if "cannot be negative" in str(e):
                        raise
                    raise ValueError("Invalid numeric counted quantity.")
        return data


class AdjustmentUpdate(BaseModel):
    product_id: Optional[int] = None
    location_id: Optional[int] = None
    counted_quantity: Optional[Decimal] = None
    reason: Optional[str] = None
    status: Optional[AdjustmentStatus] = None

    @model_validator(mode="after")
    def validate_update(self) -> "AdjustmentUpdate":
        if self.status is not None:
            if self.status in (AdjustmentStatus.DONE, AdjustmentStatus.CANCELED):
                raise ValueError(
                    "Direct status change to DONE or CANCELED is not allowed via PATCH. Use /validate or /cancel."
                )
        if self.counted_quantity is not None and self.counted_quantity < Decimal("0"):
            raise ValueError("Counted quantity cannot be negative.")
        return self


class AdjustmentResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    sku: Optional[str] = None
    location_id: int
    location_name: Optional[str] = None
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    system_quantity: Decimal
    counted_quantity: Decimal
    difference: Decimal
    reason: Optional[str] = None
    status: str
    created_by: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
