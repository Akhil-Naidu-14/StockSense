from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.middleware import get_current_active_user
from app.models import Category, Inventory, Location, Product, ReorderRule, User
from app.schemas.inventory import InventoryStockRead, LowStockResponse

router = APIRouter(prefix="/api/inventory", tags=["Inventory (Read-Only)"])


def _evaluate_inventory_item(db: Session, inv: Inventory) -> LowStockResponse:
    prod = inv.product
    loc = inv.location
    wh = loc.warehouse if loc else None
    cat = prod.category if prod else None

    avail = inv.quantity - inv.reserved_quantity

    # 1. Location-specific active ReorderRule
    rule = (
        db.query(ReorderRule)
        .filter(
            ReorderRule.product_id == inv.product_id,
            ReorderRule.location_id == inv.location_id,
            ReorderRule.active.is_(True),
        )
        .first()
    )

    # 2. Product-wide active ReorderRule fallback
    if not rule:
        rule = (
            db.query(ReorderRule)
            .filter(
                ReorderRule.product_id == inv.product_id,
                ReorderRule.location_id.is_(None),
                ReorderRule.active.is_(True),
            )
            .first()
        )

    if rule:
        min_qty = rule.minimum_quantity
        reorder_qty = rule.reorder_quantity
    else:
        min_qty = prod.reorder_level if prod else Decimal("0.0000")
        reorder_qty = prod.reorder_quantity if prod else Decimal("0.0000")

    is_low = avail <= min_qty
    is_out = avail <= Decimal("0.0000")

    return LowStockResponse(
        product_id=inv.product_id,
        product_name=prod.name if prod else "",
        sku=prod.sku if prod else "",
        category_id=prod.category_id if prod else None,
        category_name=cat.name if cat else None,
        location_id=inv.location_id,
        location_name=loc.name if loc else "",
        location_code=loc.code if loc else "",
        warehouse_id=loc.warehouse_id if loc else 0,
        warehouse_name=wh.name if wh else "",
        quantity=inv.quantity,
        reserved_quantity=inv.reserved_quantity,
        available_quantity=avail,
        minimum_quantity=min_qty,
        reorder_quantity=reorder_qty,
        is_low_stock=is_low,
        is_out_of_stock=is_out,
    )


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
    "/low-stock",
    response_model=List[LowStockResponse],
    summary="Get low-stock inventory items violating reorder thresholds",
)
def get_low_stock_inventory(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Read-only endpoint returning inventory items where available_quantity <= effective reorder threshold.
    Respects precedence: Location ReorderRule > Product ReorderRule > Product.reorder_level.
    """
    query = (
        db.query(Inventory)
        .join(Product, Inventory.product_id == Product.id)
        .join(Location, Inventory.location_id == Location.id)
        .filter(Product.is_active.is_(True), Location.is_active.is_(True))
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
    results: List[LowStockResponse] = []

    for inv in records:
        eval_item = _evaluate_inventory_item(db, inv)
        if eval_item.is_low_stock:
            results.append(eval_item)

    return results


@router.get(
    "/out-of-stock",
    response_model=List[LowStockResponse],
    summary="Get out-of-stock inventory items (available stock <= 0)",
)
def get_out_of_stock_inventory(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Read-only endpoint returning inventory items where available_quantity <= 0.
    """
    query = (
        db.query(Inventory)
        .join(Product, Inventory.product_id == Product.id)
        .join(Location, Inventory.location_id == Location.id)
        .filter(Product.is_active.is_(True), Location.is_active.is_(True))
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
    results: List[LowStockResponse] = []

    for inv in records:
        eval_item = _evaluate_inventory_item(db, inv)
        if eval_item.is_out_of_stock:
            results.append(eval_item)

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
