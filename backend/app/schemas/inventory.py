from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class InventoryStockRead(BaseModel):
    inventory_id: int
    product_id: int
    product_name: str
    sku: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    warehouse_id: int
    warehouse_name: str
    location_id: int
    location_name: str
    quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LowStockResponse(BaseModel):
    product_id: int
    product_name: str
    sku: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    location_id: int
    location_name: str
    location_code: str
    warehouse_id: int
    warehouse_name: str
    quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    minimum_quantity: Decimal
    reorder_quantity: Decimal
    is_low_stock: bool
    is_out_of_stock: bool

    model_config = ConfigDict(from_attributes=True)
