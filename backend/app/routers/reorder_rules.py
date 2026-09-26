from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user, require_roles
from app.models.enums import UserRole
from app.models.models import User
from app.schemas.reorder_rule import (
    ReorderRuleCreate,
    ReorderRuleResponse,
    ReorderRuleUpdate,
)
from app.services.reorder_service import ReorderService

router = APIRouter(prefix="/api/reorder-rules", tags=["Reorder Rules"])


@router.post(
    "",
    response_model=ReorderRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new reorder threshold rule",
)
def create_reorder_rule(
    payload: ReorderRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Create a new product-wide or location-specific reorder rule. Manager only."""
    return ReorderService.create_reorder_rule(db=db, payload=payload)


@router.get(
    "",
    response_model=List[ReorderRuleResponse],
    summary="List reorder rules with optional filtering",
)
def list_reorder_rules(
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    active_only: Optional[bool] = Query(None, description="Filter active rules only"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List reorder rules. Accessible to all authenticated operational users."""
    return ReorderService.list_reorder_rules(
        db=db,
        product_id=product_id,
        location_id=location_id,
        warehouse_id=warehouse_id,
        active_only=active_only,
    )


@router.get(
    "/{id}",
    response_model=ReorderRuleResponse,
    summary="Get reorder rule details by ID",
)
def get_reorder_rule(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get single reorder rule. Accessible to all authenticated operational users."""
    return ReorderService.get_reorder_rule(db=db, rule_id=id)


@router.patch(
    "/{id}",
    response_model=ReorderRuleResponse,
    summary="Update a reorder rule",
)
def update_reorder_rule(
    id: int,
    payload: ReorderRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Update reorder rule minimum/reorder quantities or active state. Manager only."""
    return ReorderService.update_reorder_rule(db=db, rule_id=id, payload=payload)


@router.delete(
    "/{id}",
    response_model=ReorderRuleResponse,
    summary="Deactivate a reorder rule",
)
def delete_reorder_rule(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Soft delete / deactivate a reorder rule. Manager only."""
    return ReorderService.delete_reorder_rule(db=db, rule_id=id)
