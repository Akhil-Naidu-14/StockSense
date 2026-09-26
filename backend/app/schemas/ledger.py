from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import LedgerTransactionType


class StockLedgerResponse(BaseModel):
    id: int
    timestamp: datetime
    product_id: int
    product_name: Optional[str] = None
    sku: Optional[str] = None
    transaction_type: str
    quantity_before: Decimal
    quantity_change: Decimal
    quantity_after: Decimal
    source_location_id: Optional[int] = None
    source_location_name: Optional[str] = None
    source_location_code: Optional[str] = None
    destination_location_id: Optional[int] = None
    destination_location_name: Optional[str] = None
    destination_location_code: Optional[str] = None
    performed_by: Optional[int] = None
    performed_by_name: Optional[str] = None
    performed_by_email: Optional[str] = None
    reference_id: Optional[str] = None
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MoveHistoryResponse(BaseModel):
    id: int
    date: datetime
    product: Optional[str] = None
    product_sku: Optional[str] = None
    product_id: int
    type: str
    source: Optional[str] = None
    source_location_id: Optional[int] = None
    destination: Optional[str] = None
    destination_location_id: Optional[int] = None
    quantity: Decimal
    user: Optional[str] = None
    performed_by: Optional[int] = None
    reference: Optional[str] = None
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
