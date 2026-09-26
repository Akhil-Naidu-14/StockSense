from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user, require_roles
from app.models import User, UserRole, Warehouse
from app.schemas.auth import MessageResponse
from app.schemas.warehouse import WarehouseCreate, WarehouseResponse, WarehouseUpdate

router = APIRouter(prefix="/api/warehouses", tags=["Warehouses"])


@router.post(
    "",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new warehouse",
)
def create_warehouse(
    payload: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Create a new warehouse (INVENTORY_MANAGER only)."""
    if payload.manager_id is not None:
        manager = db.query(User).filter(User.id == payload.manager_id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager user not found",
            )

    existing = db.query(Warehouse).filter(Warehouse.code == payload.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Warehouse with code '{payload.code}' already exists",
        )

    warehouse = Warehouse(
        name=payload.name,
        code=payload.code,
        address=payload.address,
        manager_id=payload.manager_id,
        is_active=True,
    )

    try:
        db.add(warehouse)
        db.commit()
        db.refresh(warehouse)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Warehouse creation conflict",
        )

    return warehouse


@router.get(
    "",
    response_model=List[WarehouseResponse],
    summary="List all warehouses",
)
def list_warehouses(
    search: Optional[str] = Query(None, description="Search by warehouse name, code, or address"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List warehouses with search and active filtering (Authenticated users)."""
    query = db.query(Warehouse)

    if is_active is not None:
        query = query.filter(Warehouse.is_active == is_active)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (Warehouse.name.ilike(term))
            | (Warehouse.code.ilike(term))
            | (Warehouse.address.ilike(term))
        )

    return query.order_by(Warehouse.code.asc()).all()


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Get a warehouse by ID",
)
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get warehouse details by ID (Authenticated users)."""
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )
    return warehouse


@router.patch(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Update a warehouse",
)
def update_warehouse(
    warehouse_id: int,
    payload: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Update warehouse details (INVENTORY_MANAGER only)."""
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    if payload.manager_id is not None and payload.manager_id != warehouse.manager_id:
        manager = db.query(User).filter(User.id == payload.manager_id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager user not found",
            )
        warehouse.manager_id = payload.manager_id

    if payload.code is not None and payload.code != warehouse.code:
        existing = (
            db.query(Warehouse)
            .filter(Warehouse.code == payload.code, Warehouse.id != warehouse_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Warehouse with code '{payload.code}' already exists",
            )
        warehouse.code = payload.code

    if payload.name is not None:
        warehouse.name = payload.name

    if payload.address is not None:
        warehouse.address = payload.address

    if payload.is_active is not None:
        warehouse.is_active = payload.is_active

    try:
        db.commit()
        db.refresh(warehouse)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Warehouse update conflict",
        )

    return warehouse


@router.delete(
    "/{warehouse_id}",
    response_model=MessageResponse,
    summary="Deactivate a warehouse",
)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Deactivate (soft-delete) a warehouse (INVENTORY_MANAGER only)."""
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    warehouse.is_active = False
    db.commit()

    return MessageResponse(message="Warehouse deactivated successfully")
