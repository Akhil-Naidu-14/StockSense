from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    category_id: Optional[int] = None
    unit_of_measure: str = Field("pcs", min_length=1, max_length=50)
    reorder_level: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    reorder_quantity: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Product name cannot be empty")
        return s

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        s = v.strip().upper()
        if not s:
            raise ValueError("Product SKU cannot be empty")
        return s


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    category_id: Optional[int] = None
    unit_of_measure: Optional[str] = Field(None, min_length=1, max_length=50)
    reorder_level: Optional[Decimal] = Field(None, ge=Decimal("0"))
    reorder_quantity: Optional[Decimal] = Field(None, ge=Decimal("0"))
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Product name cannot be empty")
            return s
        return v

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip().upper()
            if not s:
                raise ValueError("Product SKU cannot be empty")
            return s
        return v


class ProductResponse(BaseModel):
    id: int
    name: str
    sku: str
    category_id: Optional[int] = None
    unit_of_measure: str
    reorder_level: Decimal
    reorder_quantity: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LocationStockDetail(BaseModel):
    location_id: int
    location_name: str
    warehouse_id: int
    warehouse_name: str
    quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal


class ProductStockResponse(BaseModel):
    product_id: int
    sku: str
    total_quantity: Decimal
    total_reserved_quantity: Decimal
    total_available_quantity: Decimal
    locations: List[LocationStockDetail]
