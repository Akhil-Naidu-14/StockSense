from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str

    model_config = ConfigDict(from_attributes=True)
