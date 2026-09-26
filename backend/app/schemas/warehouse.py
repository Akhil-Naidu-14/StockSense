from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class WarehouseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    address: Optional[str] = None
    manager_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Warehouse name cannot be empty")
        return s

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        s = v.strip().upper()
        if not s:
            raise ValueError("Warehouse code cannot be empty")
        return s


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    address: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Warehouse name cannot be empty")
            return s
        return v

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip().upper()
            if not s:
                raise ValueError("Warehouse code cannot be empty")
            return s
        return v


class WarehouseResponse(BaseModel):
    id: int
    name: str
    code: str
    address: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
