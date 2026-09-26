from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.middleware import get_current_active_user
from app.models import Category, Inventory, Location, Product, User
from app.schemas.inventory import InventoryStockRead

router = APIRouter(prefix="/api/inventory", tags=["Inventory (Read-Only)"])


@router.get(
    "",
    response_model=List[InventoryStockRead],
    summary="Query stock availability across locations (Read-Only)",
)
def list_inventory(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    category_id: Optional[int] = Query(None, description="Filter by product category ID"),
    low_stock: Optional[bool] = Query(None, description="Filter items where available stock <= reorder level"),
    out_of_stock: Optional[bool] = Query(None, description="Filter items where available stock <= 0"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Read-only inventory availability query across products, locations, and warehouses.
    available_quantity = quantity - reserved_quantity
    """
    query = (
        db.query(Inventory)
        .join(Product, Inventory.product_id == Product.id)
        .join(Location, Inventory.location_id == Location.id)
        .options(
            joinedload(Inventory.product).joinedload(Product.category),
            joinedload(Inventory.location).joinedload(Location.warehouse),
        )
    )

    if warehouse_id is not None:
        query = query.filter(Location.warehouse_id == warehouse_id)

    if location_id is not None:
        query = query.filter(Inventory.location_id == location_id)

    if product_id is not None:
        query = query.filter(Inventory.product_id == product_id)

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    records = query.all()
    results: List[InventoryStockRead] = []

    for inv in records:
        prod = inv.product
        loc = inv.location
        wh = loc.warehouse
        cat = prod.category if prod else None

        qty = inv.quantity
        res = inv.reserved_quantity
        avail = qty - res

        if out_of_stock and avail > Decimal("0.0000"):
            continue

        if low_stock and prod and avail > prod.reorder_level:
            continue

        results.append(
            InventoryStockRead(
                inventory_id=inv.id,
                product_id=inv.product_id,
                product_name=prod.name if prod else "",
                sku=prod.sku if prod else "",
                category_id=prod.category_id if prod else None,
                category_name=cat.name if cat else None,
                warehouse_id=loc.warehouse_id,
                warehouse_name=wh.name if wh else "",
                location_id=inv.location_id,
                location_name=loc.name if loc else "",
                quantity=qty,
                reserved_quantity=res,
                available_quantity=avail,
                updated_at=inv.updated_at,
            )
        )

    return results


@router.get(
    "/{product_id}/locations",
    response_model=List[InventoryStockRead],
    summary="Get stock details for a specific product across all locations",
)
def get_product_location_inventory(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get location-by-location inventory records for a given product (Read-Only)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    records = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .options(
            joinedload(Inventory.product).joinedload(Product.category),
            joinedload(Inventory.location).joinedload(Location.warehouse),
        )
        .all()
    )

    results: List[InventoryStockRead] = []
    for inv in records:
        prod = inv.product
        loc = inv.location
        wh = loc.warehouse
        cat = prod.category if prod else None

        qty = inv.quantity
        res = inv.reserved_quantity
        avail = qty - res

        results.append(
            InventoryStockRead(
                inventory_id=inv.id,
                product_id=inv.product_id,
                product_name=prod.name if prod else "",
                sku=prod.sku if prod else "",
                category_id=prod.category_id if prod else None,
                category_name=cat.name if cat else None,
                warehouse_id=loc.warehouse_id,
                warehouse_name=wh.name if wh else "",
                location_id=inv.location_id,
                location_name=loc.name if loc else "",
                quantity=qty,
                reserved_quantity=res,
                available_quantity=avail,
                updated_at=inv.updated_at,
            )
        )

    return results
