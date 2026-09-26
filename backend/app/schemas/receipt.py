from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReceiptItemCreate(BaseModel):
    product_id: int
    quantity: Decimal
    received_quantity: Optional[Decimal] = None

    @model_validator(mode="before")
    @classmethod
    def validate_item(cls, data: Any) -> Any:
        if isinstance(data, dict):
            qty_raw = data.get("quantity")
            if qty_raw is not None:
                try:
                    qty = Decimal(str(qty_raw))
                    if qty <= Decimal("0"):
                        raise ValueError("Requested quantity must be greater than zero.")
                    data["quantity"] = qty
                except (ValueError, TypeError) as e:
                    if "greater than zero" in str(e):
                        raise
                    raise ValueError("Invalid numeric quantity.")

            rec_raw = data.get("received_quantity")
            if rec_raw is not None:
                try:
                    rec_qty = Decimal(str(rec_raw))
                    if rec_qty < Decimal("0"):
                        raise ValueError("Received quantity cannot be negative.")
                    data["received_quantity"] = rec_qty
                except (ValueError, TypeError) as e:
                    if "cannot be negative" in str(e):
                        raise
                    raise ValueError("Invalid numeric received quantity.")
            else:
                # Default received_quantity to quantity if omitted
                if "quantity" in data and isinstance(data["quantity"], Decimal):
                    data["received_quantity"] = data["quantity"]

            if (
                data.get("quantity") is not None
                and data.get("received_quantity") is not None
            ):
                if data["received_quantity"] > data["quantity"]:
                    raise ValueError(
                        "Received quantity cannot exceed requested/ordered quantity."
                    )
        return data


class ReceiptCreate(BaseModel):
    supplier: Optional[str] = None
    location_id: int
    items: List[ReceiptItemCreate]

    @model_validator(mode="after")
    def validate_items_list(self) -> "ReceiptCreate":
        if not self.items or len(self.items) == 0:
            raise ValueError("Receipt must contain at least one item.")

        seen_products = set()
        for item in self.items:
            if item.product_id in seen_products:
                raise ValueError(
                    f"Duplicate product_id {item.product_id} in receipt items is not allowed."
                )
            seen_products.add(item.product_id)
        return self


class ReceiptUpdate(BaseModel):
    supplier: Optional[str] = None
    location_id: Optional[int] = None
    items: Optional[List[ReceiptItemCreate]] = None

    @model_validator(mode="after")
    def validate_items_update(self) -> "ReceiptUpdate":
        if self.items is not None:
            if len(self.items) == 0:
                raise ValueError("Receipt items list cannot be empty.")

            seen_products = set()
            for item in self.items:
                if item.product_id in seen_products:
                    raise ValueError(
                        f"Duplicate product_id {item.product_id} in receipt items is not allowed."
                    )
                seen_products.add(item.product_id)
        return self


class ReceiptItemResponse(BaseModel):
    id: int
    receipt_id: int
    product_id: int
    product_name: Optional[str] = None
    sku: Optional[str] = None
    quantity: Decimal
    received_quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class ReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    supplier: Optional[str] = None
    location_id: int
    location_name: Optional[str] = None
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    items: List[ReceiptItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
