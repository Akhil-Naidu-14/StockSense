from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user, require_roles
from app.models import AdjustmentStatus, User, UserRole
from app.schemas.adjustment import (
    AdjustmentCreate,
    AdjustmentResponse,
    AdjustmentUpdate,
)
from app.services.adjustment_service import AdjustmentService

router = APIRouter(prefix="/api/adjustments", tags=["Adjustments"])


@router.post(
    "",
    response_model=AdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new stock adjustment document in DRAFT status",
)
def create_adjustment(
    payload: AdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """
    Create a new adjustment document in DRAFT status.
    Does NOT mutate inventory or create stock ledgers until validated.
    """
    return AdjustmentService.create_adjustment(db=db, payload=payload, current_user=current_user)


@router.get(
    "",
    response_model=List[AdjustmentResponse],
    summary="List all adjustments with optional filtering",
)
def list_adjustments(
    status: Optional[AdjustmentStatus] = Query(None, description="Filter by adjustment status"),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    search: Optional[str] = Query(None, description="Search product name, SKU, or reason"),
    created_by: Optional[int] = Query(None, description="Filter by creator user ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List adjustments ordered by newest first with filters."""
    return AdjustmentService.list_adjustments(
        db=db,
        status_filter=status,
        product_id=product_id,
        location_id=location_id,
        warehouse_id=warehouse_id,
        search=search,
        created_by=created_by,
    )


@router.get(
    "/{id}",
    response_model=AdjustmentResponse,
    summary="Get detailed information for an adjustment",
)
def get_adjustment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve detailed adjustment info including product and location metadata."""
    return AdjustmentService.get_adjustment(db=db, adjustment_id=id)


@router.patch(
    "/{id}",
    response_model=AdjustmentResponse,
    summary="Update a pre-validation adjustment",
)
def update_adjustment(
    id: int,
    payload: AdjustmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """Update product_id, location_id, counted_quantity, reason, or status of a pre-validation adjustment."""
    return AdjustmentService.update_adjustment(db=db, adjustment_id=id, payload=payload)


@router.post(
    "/{id}/validate",
    response_model=AdjustmentResponse,
    summary="Validate adjustment and adjust inventory physical stock",
)
def validate_adjustment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """
    Validate an adjustment, setting physical stock via InventoryService.adjust_stock in a single transaction.
    Marks adjustment status as DONE.
    """
    return AdjustmentService.validate_adjustment(
        db=db, adjustment_id=id, current_user=current_user
    )


@router.post(
    "/{id}/cancel",
    response_model=AdjustmentResponse,
    summary="Cancel a pre-DONE adjustment",
)
def cancel_adjustment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """Cancel a pre-DONE adjustment document. Does not change inventory."""
    return AdjustmentService.cancel_adjustment(db=db, adjustment_id=id)
