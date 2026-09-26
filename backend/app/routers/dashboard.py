from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user
from app.models.models import User
from app.schemas.dashboard import DashboardKPIResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get(
    "",
    response_model=DashboardKPIResponse,
    summary="Get operational dashboard KPI metrics",
)
def get_dashboard_kpis(
    warehouse_id: Optional[int] = Query(None, description="Filter KPIs by warehouse ID"),
    location_id: Optional[int] = Query(None, description="Filter KPIs by location ID"),
    category_id: Optional[int] = Query(None, description="Filter KPIs by product category ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Read-only dashboard summary returning total products, low-stock count,
    out-of-stock count, pending receipts, pending deliveries, and scheduled transfers.
    Accessible to all authenticated operational users (INVENTORY_MANAGER, WAREHOUSE_STAFF).
    """
    return DashboardService.get_kpis(
        db=db,
        warehouse_id=warehouse_id,
        location_id=location_id,
        category_id=category_id,
    )
