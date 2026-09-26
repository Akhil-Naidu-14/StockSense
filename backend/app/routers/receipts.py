from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user, require_roles
from app.models import ReceiptStatus, User, UserRole
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptResponse,
    ReceiptUpdate,
)
from app.services.receipt_service import ReceiptService

router = APIRouter(prefix="/api/receipts", tags=["Receipts"])


@router.post(
    "",
    response_model=ReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new incoming receipt in DRAFT status",
)
def create_receipt(
    payload: ReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """
    Create a new receipt document (DRAFT status).
    Does NOT mutate inventory or create stock ledgers until validated.
    """
    return ReceiptService.create_receipt(db=db, payload=payload, current_user=current_user)


@router.get(
    "",
    response_model=List[ReceiptResponse],
    summary="List all receipts with optional filtering",
)
def list_receipts(
    status: Optional[ReceiptStatus] = Query(None, description="Filter by receipt status"),
    location_id: Optional[int] = Query(None, description="Filter by destination location ID"),
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    supplier: Optional[str] = Query(None, description="Filter by supplier substring"),
    search: Optional[str] = Query(None, description="Search receipt_number or supplier"),
    created_by: Optional[int] = Query(None, description="Filter by creator user ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List receipts ordered by newest first with filters."""
    return ReceiptService.list_receipts(
        db=db,
        status_filter=status,
        location_id=location_id,
        warehouse_id=warehouse_id,
        supplier=supplier,
        search=search,
        created_by=created_by,
    )


@router.get(
    "/{receipt_id}",
    response_model=ReceiptResponse,
    summary="Get detailed information for a receipt",
)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve detailed receipt info including items and location/warehouse metadata."""
    return ReceiptService.get_receipt(db=db, receipt_id=receipt_id)


@router.patch(
    "/{receipt_id}",
    response_model=ReceiptResponse,
    summary="Update a DRAFT receipt",
)
def update_receipt(
    receipt_id: int,
    payload: ReceiptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """Update supplier, location, or items of a DRAFT receipt."""
    return ReceiptService.update_receipt(db=db, receipt_id=receipt_id, payload=payload)


@router.post(
    "/{receipt_id}/validate",
    response_model=ReceiptResponse,
    summary="Validate receipt and mutate inventory stock",
)
def validate_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """
    Validate a DRAFT receipt, executing stock increases via InventoryService in a single transaction.
    Marks receipt status as DONE.
    """
    return ReceiptService.validate_receipt(
        db=db, receipt_id=receipt_id, current_user=current_user
    )


@router.post(
    "/{receipt_id}/cancel",
    response_model=ReceiptResponse,
    summary="Cancel a DRAFT receipt",
)
def cancel_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """Cancel a DRAFT receipt before validation. Does not change inventory."""
    return ReceiptService.cancel_receipt(db=db, receipt_id=receipt_id)
