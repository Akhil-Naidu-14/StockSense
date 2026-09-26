from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user, require_roles
from app.models import Category, Inventory, Product, User, UserRole
from app.schemas.auth import MessageResponse
from app.schemas.product import (
    LocationStockDetail,
    ProductCreate,
    ProductResponse,
    ProductStockResponse,
    ProductUpdate,
)

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """
    Create a new product master record (INVENTORY_MANAGER only).
    Note: Initial stock setup is deferred to the centralized InventoryService.
    """
    if payload.category_id is not None:
        category = db.query(Category).filter(Category.id == payload.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced category not found",
            )

    existing = db.query(Product).filter(Product.sku == payload.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU '{payload.sku}' already exists",
        )

    product = Product(
        name=payload.name,
        sku=payload.sku,
        category_id=payload.category_id,
        unit_of_measure=payload.unit_of_measure,
        reorder_level=payload.reorder_level,
        reorder_quantity=payload.reorder_quantity,
        is_active=True,
    )

    try:
        db.add(product)
        db.commit()
        db.refresh(product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product creation conflict",
        )

    return product


@router.get(
    "",
    response_model=List[ProductResponse],
    summary="List all products",
)
def list_products(
    search: Optional[str] = Query(None, description="Search by product name or SKU"),
    sku: Optional[str] = Query(None, description="Filter by exact SKU"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List products with filtering by search term, SKU, category, and active status (Authenticated users)."""
    query = db.query(Product)

    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    if sku:
        query = query.filter(Product.sku == sku.strip().upper())

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (Product.name.ilike(term)) | (Product.sku.ilike(term))
        )

    return query.order_by(Product.name.asc()).all()


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product by ID",
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get product details by ID (Authenticated users)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Update product details (INVENTORY_MANAGER only)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if payload.category_id is not None and payload.category_id != product.category_id:
        category = db.query(Category).filter(Category.id == payload.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced category not found",
            )
        product.category_id = payload.category_id

    if payload.sku is not None and payload.sku != product.sku:
        existing = (
            db.query(Product)
            .filter(Product.sku == payload.sku, Product.id != product_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product with SKU '{payload.sku}' already exists",
            )
        product.sku = payload.sku

    if payload.name is not None:
        product.name = payload.name

    if payload.unit_of_measure is not None:
        product.unit_of_measure = payload.unit_of_measure

    if payload.reorder_level is not None:
        product.reorder_level = payload.reorder_level

    if payload.reorder_quantity is not None:
        product.reorder_quantity = payload.reorder_quantity

    if payload.is_active is not None:
        product.is_active = payload.is_active

    try:
        db.commit()
        db.refresh(product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product update conflict",
        )

    return product


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    summary="Deactivate a product",
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.INVENTORY_MANAGER)),
):
    """Deactivate (soft-delete) a product (INVENTORY_MANAGER only)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    product.is_active = False
    db.commit()

    return MessageResponse(message="Product deactivated successfully")


@router.get(
    "/{product_id}/stock",
    response_model=ProductStockResponse,
    summary="Get aggregated product stock availability by location",
)
def get_product_stock(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Read-only endpoint returning product stock across all locations.
    available_quantity = quantity - reserved_quantity
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    inventories = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .all()
    )

    location_details: List[LocationStockDetail] = []
    total_qty = Decimal("0.0000")
    total_reserved = Decimal("0.0000")
    total_available = Decimal("0.0000")

    for inv in inventories:
        qty = inv.quantity
        res = inv.reserved_quantity
        avail = qty - res

        total_qty += qty
        total_reserved += res
        total_available += avail

        location_details.append(
            LocationStockDetail(
                location_id=inv.location_id,
                location_name=inv.location.name,
                warehouse_id=inv.location.warehouse_id,
                warehouse_name=inv.location.warehouse.name,
                quantity=qty,
                reserved_quantity=res,
                available_quantity=avail,
            )
        )

    return ProductStockResponse(
        product_id=product.id,
        sku=product.sku,
        total_quantity=total_qty,
        total_reserved_quantity=total_reserved,
        total_available_quantity=total_available,
        locations=location_details,
    )
