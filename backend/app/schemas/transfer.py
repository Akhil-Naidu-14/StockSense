from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import TransferStatus


class TransferItemCreate(BaseModel):
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
                        raise ValueError("Transfer quantity must be greater than zero.")
                    data["quantity"] = qty
                except (ValueError, TypeError) as e:
                    if "greater than zero" in str(e):
                        raise
                    raise ValueError("Invalid numeric quantity.")
        return data


class TransferCreate(BaseModel):
    source_location_id: int
    destination_location_id: int
    items: List[TransferItemCreate]

    @model_validator(mode="after")
    def validate_transfer_payload(self) -> "TransferCreate":
        if self.source_location_id == self.destination_location_id:
            raise ValueError("Source and destination locations cannot be identical.")

        if not self.items or len(self.items) == 0:
            raise ValueError("Transfer must contain at least one item.")

        seen_products = set()
        for item in self.items:
            if item.product_id in seen_products:
                raise ValueError(
                    f"Duplicate product_id {item.product_id} in transfer items is not allowed."
                )
            seen_products.add(item.product_id)
        return self


class TransferUpdate(BaseModel):
    source_location_id: Optional[int] = None
    destination_location_id: Optional[int] = None
    status: Optional[TransferStatus] = None
    items: Optional[List[TransferItemCreate]] = None

    @model_validator(mode="after")
    def validate_transfer_update(self) -> "TransferUpdate":
        if self.status is not None:
            if self.status in (TransferStatus.DONE, TransferStatus.CANCELED):
                raise ValueError(
                    "Direct status change to DONE or CANCELED is not allowed via PATCH. Use /validate or /cancel."
                )

        if self.source_location_id is not None and self.destination_location_id is not None:
            if self.source_location_id == self.destination_location_id:
                raise ValueError("Source and destination locations cannot be identical.")

        if self.items is not None:
            if len(self.items) == 0:
                raise ValueError("Transfer items list cannot be empty.")

            seen_products = set()
            for item in self.items:
                if item.product_id in seen_products:
                    raise ValueError(
                        f"Duplicate product_id {item.product_id} in transfer items is not allowed."
                    )
                seen_products.add(item.product_id)
        return self


class TransferItemResponse(BaseModel):
    id: int
    transfer_id: int
    product_id: int
    product_name: Optional[str] = None
    sku: Optional[str] = None
    quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class TransferResponse(BaseModel):
    id: int
    transfer_number: str
    source_location_id: int
    source_location_name: Optional[str] = None
    source_warehouse_id: Optional[int] = None
    source_warehouse_name: Optional[str] = None
    destination_location_id: int
    destination_location_name: Optional[str] = None
    destination_warehouse_id: Optional[int] = None
    destination_warehouse_name: Optional[str] = None
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    items: List[TransferItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
