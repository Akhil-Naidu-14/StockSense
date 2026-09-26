from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocationCreate(BaseModel):
    warehouse_id: int
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    location_type: str = Field("internal", min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Location name cannot be empty")
        return s

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        s = v.strip().upper()
        if not s:
            raise ValueError("Location code cannot be empty")
        return s


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    location_type: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Location name cannot be empty")
            return s
        return v

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip().upper()
            if not s:
                raise ValueError("Location code cannot be empty")
            return s
        return v


class LocationResponse(BaseModel):
    id: int
    warehouse_id: int
    name: str
    code: str
    location_type: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
