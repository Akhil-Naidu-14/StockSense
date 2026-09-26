from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user, require_roles
from app.models import DeliveryStatus, User, UserRole
from app.schemas.delivery import (
    DeliveryCreate,
    DeliveryResponse,
    DeliveryUpdate,
)
from app.services.delivery_service import DeliveryService

router = APIRouter(prefix="/api/deliveries", tags=["Deliveries"])


@router.post(
    "",
    response_model=DeliveryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new delivery in DRAFT status",
)
def create_delivery(
    payload: DeliveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """
    Create a new delivery document in DRAFT status.
    Does NOT mutate inventory or create stock ledgers until validated.
    """
    return DeliveryService.create_delivery(db=db, payload=payload, current_user=current_user)


@router.get(
    "",
    response_model=List[DeliveryResponse],
    summary="List all deliveries with optional filtering",
)
def list_deliveries(
    status: Optional[DeliveryStatus] = Query(None, description="Filter by delivery status"),
    location_id: Optional[int] = Query(None, description="Filter by source location ID"),
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    customer_reference: Optional[str] = Query(None, description="Filter by customer reference substring"),
    search: Optional[str] = Query(None, description="Search delivery_number or customer_reference"),
    created_by: Optional[int] = Query(None, description="Filter by creator user ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List deliveries ordered by newest first with filters."""
    return DeliveryService.list_deliveries(
        db=db,
        status_filter=status,
        location_id=location_id,
        warehouse_id=warehouse_id,
        customer_reference=customer_reference,
        search=search,
        created_by=created_by,
    )


@router.get(
    "/{delivery_id}",
    response_model=DeliveryResponse,
    summary="Get detailed information for a delivery",
)
def get_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve detailed delivery info including items and location/warehouse metadata."""
    return DeliveryService.get_delivery(db=db, delivery_id=delivery_id)


@router.patch(
    "/{delivery_id}",
    response_model=DeliveryResponse,
    summary="Update a pre-terminal delivery",
)
def update_delivery(
    delivery_id: int,
    payload: DeliveryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """Update customer_reference, location_id, operational status, or items of a pre-terminal delivery."""
    return DeliveryService.update_delivery(db=db, delivery_id=delivery_id, payload=payload)


@router.post(
    "/{delivery_id}/validate",
    response_model=DeliveryResponse,
    summary="Validate delivery and mutate inventory stock",
)
def validate_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """
    Validate a pre-terminal delivery, executing stock decreases via InventoryService in a single transaction.
    Marks delivery status as DONE.
    """
    return DeliveryService.validate_delivery(
        db=db, delivery_id=delivery_id, current_user=current_user
    )


@router.post(
    "/{delivery_id}/cancel",
    response_model=DeliveryResponse,
    summary="Cancel a pre-DONE delivery",
)
def cancel_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """Cancel a pre-DONE delivery document. Does not change inventory."""
    return DeliveryService.cancel_delivery(db=db, delivery_id=delivery_id)
