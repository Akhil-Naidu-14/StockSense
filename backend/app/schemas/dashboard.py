from typing import Optional
from pydantic import BaseModel, ConfigDict


class DashboardKPIResponse(BaseModel):
    total_products: int
    low_stock_items: int
    out_of_stock_items: int
    pending_receipts: int
    pending_deliveries: int
    scheduled_transfers: int

    model_config = ConfigDict(from_attributes=True)
