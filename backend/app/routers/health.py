from fastapi import APIRouter
from app.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint to verify backend operational status."""
    return HealthResponse(
        status="ok",
        app_name="StockSense API",
        environment=settings.APP_ENV,
    )
