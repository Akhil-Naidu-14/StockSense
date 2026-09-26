from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user, require_roles
from app.models import Category, User, UserRole
from app.schemas.auth import MessageResponse
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product category",
)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Create a new product category (INVENTORY_MANAGER only)."""
    existing = (
        db.query(Category)
        .filter(Category.name.ilike(payload.name))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this name already exists",
        )

    category = Category(
        name=payload.name,
        description=payload.description,
        is_active=True,
    )

    try:
        db.add(category)
        db.commit()
        db.refresh(category)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category creation conflict",
        )

    return category


@router.get(
    "",
    response_model=List[CategoryResponse],
    summary="List all product categories",
)
def list_categories(
    search: Optional[str] = Query(None, description="Search by category name or description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List product categories with search and status filtering (Authenticated users)."""
    query = db.query(Category)

    if is_active is not None:
        query = query.filter(Category.is_active == is_active)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (Category.name.ilike(search_term)) | (Category.description.ilike(search_term))
        )

    return query.order_by(Category.name.asc()).all()


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get a category by ID",
)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a category by ID (Authenticated users)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update a category",
)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Update category details (INVENTORY_MANAGER only)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    if payload.name is not None and payload.name.lower() != category.name.lower():
        existing = (
            db.query(Category)
            .filter(Category.name.ilike(payload.name), Category.id != category_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category with this name already exists",
            )
        category.name = payload.name

    if payload.description is not None:
        category.description = payload.description

    if payload.is_active is not None:
        category.is_active = payload.is_active

    try:
        db.commit()
        db.refresh(category)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category update conflict",
        )

    return category


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    summary="Deactivate a category",
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Deactivate (soft-delete) a category (INVENTORY_MANAGER only)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    category.is_active = False
    db.commit()

    return MessageResponse(message="Category deactivated successfully")
