from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import DeliveryStatus


class DeliveryItemCreate(BaseModel):
    product_id: int
    quantity: Decimal

    @model_validator(mode="before")
    @classmethod
    def validate_item(cls, data: Any) -> Any:
        if isinstance(data, dict):
            qty_raw = data.get("quantity")
            if qty_raw is not None:
                try:
                    qty = Decimal(str(qty_raw))
                    if qty <= Decimal("0"):
                        raise ValueError("Requested delivery quantity must be greater than zero.")
                    data["quantity"] = qty
                except (ValueError, TypeError) as e:
                    if "greater than zero" in str(e):
                        raise
                    raise ValueError("Invalid numeric quantity.")
        return data


class DeliveryCreate(BaseModel):
    customer_reference: Optional[str] = None
    location_id: int
    items: List[DeliveryItemCreate]

    @model_validator(mode="after")
    def validate_items_list(self) -> "DeliveryCreate":
        if not self.items or len(self.items) == 0:
            raise ValueError("Delivery must contain at least one item.")

        seen_products = set()
        for item in self.items:
            if item.product_id in seen_products:
                raise ValueError(
                    f"Duplicate product_id {item.product_id} in delivery items is not allowed."
                )
            seen_products.add(item.product_id)
        return self


class DeliveryUpdate(BaseModel):
    customer_reference: Optional[str] = None
    location_id: Optional[int] = None
    status: Optional[DeliveryStatus] = None
    items: Optional[List[DeliveryItemCreate]] = None

    @model_validator(mode="after")
    def validate_items_update(self) -> "DeliveryUpdate":
        if self.status is not None:
            if self.status in (DeliveryStatus.DONE, DeliveryStatus.CANCELED):
                raise ValueError(
                    "Direct status change to DONE or CANCELED is not allowed via PATCH. Use /validate or /cancel."
                )

        if self.items is not None:
            if len(self.items) == 0:
                raise ValueError("Delivery items list cannot be empty.")

            seen_products = set()
            for item in self.items:
                if item.product_id in seen_products:
                    raise ValueError(
                        f"Duplicate product_id {item.product_id} in delivery items is not allowed."
                    )
                seen_products.add(item.product_id)
        return self


class DeliveryItemResponse(BaseModel):
    id: int
    delivery_id: int
    product_id: int
    product_name: Optional[str] = None
    sku: Optional[str] = None
    quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class DeliveryResponse(BaseModel):
    id: int
    delivery_number: str
    customer_reference: Optional[str] = None
    location_id: int
    location_name: Optional[str] = None
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    items: List[DeliveryItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
