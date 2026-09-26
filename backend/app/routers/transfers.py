from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user, require_roles
from app.models import TransferStatus, User, UserRole
from app.schemas.transfer import (
    TransferCreate,
    TransferResponse,
    TransferUpdate,
)
from app.services.transfer_service import TransferService

router = APIRouter(prefix="/api/transfers", tags=["Transfers"])


@router.post(
    "",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new internal transfer in DRAFT status",
)
def create_transfer(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """
    Create a new transfer document in DRAFT status.
    Does NOT mutate inventory or create stock ledgers until validated.
    """
    return TransferService.create_transfer(db=db, payload=payload, current_user=current_user)


@router.get(
    "",
    response_model=List[TransferResponse],
    summary="List all transfers with optional filtering",
)
def list_transfers(
    status: Optional[TransferStatus] = Query(None, description="Filter by transfer status"),
    source_location_id: Optional[int] = Query(None, description="Filter by source location ID"),
    destination_location_id: Optional[int] = Query(None, description="Filter by destination location ID"),
    source_warehouse_id: Optional[int] = Query(None, description="Filter by source warehouse ID"),
    destination_warehouse_id: Optional[int] = Query(None, description="Filter by destination warehouse ID"),
    search: Optional[str] = Query(None, description="Search transfer_number"),
    created_by: Optional[int] = Query(None, description="Filter by creator user ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List transfers ordered by newest first with filters."""
    return TransferService.list_transfers(
        db=db,
        status_filter=status,
        source_location_id=source_location_id,
        destination_location_id=destination_location_id,
        source_warehouse_id=source_warehouse_id,
        destination_warehouse_id=destination_warehouse_id,
        search=search,
        created_by=created_by,
    )


@router.get(
    "/{transfer_id}",
    response_model=TransferResponse,
    summary="Get detailed information for a transfer",
)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve detailed transfer info including items and location/warehouse metadata."""
    return TransferService.get_transfer(db=db, transfer_id=transfer_id)


@router.patch(
    "/{transfer_id}",
    response_model=TransferResponse,
    summary="Update a pre-terminal transfer",
)
def update_transfer(
    transfer_id: int,
    payload: TransferUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """Update source_location_id, destination_location_id, operational status, or items of a pre-terminal transfer."""
    return TransferService.update_transfer(db=db, transfer_id=transfer_id, payload=payload)


@router.post(
    "/{transfer_id}/validate",
    response_model=TransferResponse,
    summary="Validate transfer and move inventory stock",
)
def validate_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """
    Validate an IN_TRANSIT transfer, executing stock movements via InventoryService.transfer_stock in a single transaction.
    Marks transfer status as DONE.
    """
    return TransferService.validate_transfer(
        db=db, transfer_id=transfer_id, current_user=current_user
    )


@router.post(
    "/{transfer_id}/cancel",
    response_model=TransferResponse,
    summary="Cancel a pre-DONE transfer",
)
def cancel_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    """Cancel a pre-DONE transfer document. Does not change inventory."""
    return TransferService.cancel_transfer(db=db, transfer_id=transfer_id)
