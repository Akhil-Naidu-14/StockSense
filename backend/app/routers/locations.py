from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user, require_roles
from app.models import Location, User, UserRole, Warehouse
from app.schemas.auth import MessageResponse
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate

router = APIRouter(prefix="/api/locations", tags=["Locations"])


@router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new location",
)
def create_location(
    payload: LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Create a new location inside a warehouse (INVENTORY_MANAGER only)."""
    warehouse = db.query(Warehouse).filter(Warehouse.id == payload.warehouse_id).first()
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced warehouse not found",
        )

    existing = db.query(Location).filter(Location.code == payload.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Location with code '{payload.code}' already exists",
        )

    location = Location(
        warehouse_id=payload.warehouse_id,
        name=payload.name,
        code=payload.code,
        location_type=payload.location_type,
        is_active=True,
    )

    try:
        db.add(location)
        db.commit()
        db.refresh(location)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Location creation conflict",
        )

    return location


@router.get(
    "",
    response_model=List[LocationResponse],
    summary="List all locations",
)
def list_locations(
    warehouse_id: Optional[int] = Query(None, description="Filter by parent warehouse ID"),
    search: Optional[str] = Query(None, description="Search by location name, code, or type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List locations with filtering by warehouse, search term, and status (Authenticated users)."""
    query = db.query(Location)

    if warehouse_id is not None:
        query = query.filter(Location.warehouse_id == warehouse_id)

    if is_active is not None:
        query = query.filter(Location.is_active == is_active)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (Location.name.ilike(term))
            | (Location.code.ilike(term))
            | (Location.location_type.ilike(term))
        )

    return query.order_by(Location.code.asc()).all()


@router.get(
    "/{location_id}",
    response_model=LocationResponse,
    summary="Get a location by ID",
)
def get_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get location details by ID (Authenticated users)."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )
    return location


@router.patch(
    "/{location_id}",
    response_model=LocationResponse,
    summary="Update a location",
)
def update_location(
    location_id: int,
    payload: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Update location details (INVENTORY_MANAGER only)."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    if payload.code is not None and payload.code != location.code:
        existing = (
            db.query(Location)
            .filter(Location.code == payload.code, Location.id != location_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location with code '{payload.code}' already exists",
            )
        location.code = payload.code

    if payload.name is not None:
        location.name = payload.name

    if payload.location_type is not None:
        location.location_type = payload.location_type

    if payload.is_active is not None:
        location.is_active = payload.is_active

    try:
        db.commit()
        db.refresh(location)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Location update conflict",
        )

    return location


@router.delete(
    "/{location_id}",
    response_model=MessageResponse,
    summary="Deactivate a location",
)
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Deactivate (soft-delete) a location (INVENTORY_MANAGER only)."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    location.is_active = False
    db.commit()

    return MessageResponse(message="Location deactivated successfully")
