from decimal import Decimal
from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased

from app.models.enums import DeliveryStatus, ReceiptStatus, TransferStatus
from app.models.models import Delivery, Inventory, Location, Product, Receipt, ReorderRule, Transfer
from app.schemas.dashboard import DashboardKPIResponse


class DashboardService:

    @classmethod
    def get_kpis(
        cls,
        db: Session,
        warehouse_id: Optional[int] = None,
        location_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> DashboardKPIResponse:
        # 1. Total active products count
        prod_query = db.query(Product).filter(Product.is_active.is_(True))
        if category_id is not None:
            prod_query = prod_query.filter(Product.category_id == category_id)
        total_products = prod_query.count()

        # 2. Low stock & out of stock inventory items count
        inv_query = (
            db.query(Inventory)
            .join(Product, Inventory.product_id == Product.id)
            .join(Location, Inventory.location_id == Location.id)
            .filter(Product.is_active.is_(True), Location.is_active.is_(True))
        )
        if warehouse_id is not None:
            inv_query = inv_query.filter(Location.warehouse_id == warehouse_id)
        if location_id is not None:
            inv_query = inv_query.filter(Inventory.location_id == location_id)
        if category_id is not None:
            inv_query = inv_query.filter(Product.category_id == category_id)

        inv_records = inv_query.all()
        low_stock_count = 0
        out_of_stock_count = 0

        for inv in inv_records:
            avail = inv.quantity - inv.reserved_quantity

            # Check location-specific rule
            rule = (
                db.query(ReorderRule)
                .filter(
                    ReorderRule.product_id == inv.product_id,
                    ReorderRule.location_id == inv.location_id,
                    ReorderRule.active.is_(True),
                )
                .first()
            )
            if not rule:
                # Check product-wide rule
                rule = (
                    db.query(ReorderRule)
                    .filter(
                        ReorderRule.product_id == inv.product_id,
                        ReorderRule.location_id.is_(None),
                        ReorderRule.active.is_(True),
                    )
                    .first()
                )

            threshold = rule.minimum_quantity if rule else (inv.product.reorder_level if inv.product else Decimal("0.0000"))

            if avail <= threshold:
                low_stock_count += 1
            if avail <= Decimal("0.0000"):
                out_of_stock_count += 1

        # 3. Pending receipts count (exclude DONE and CANCELED)
        rcp_query = db.query(Receipt).filter(
            Receipt.status.notin_([ReceiptStatus.DONE, ReceiptStatus.CANCELED])
        )
        if location_id is not None:
            rcp_query = rcp_query.filter(Receipt.location_id == location_id)
        elif warehouse_id is not None:
            rcp_query = rcp_query.join(Location, Receipt.location_id == Location.id).filter(
                Location.warehouse_id == warehouse_id
            )
        pending_receipts = rcp_query.count()

        # 4. Pending deliveries count (exclude DONE and CANCELED)
        del_query = db.query(Delivery).filter(
            Delivery.status.notin_([DeliveryStatus.DONE, DeliveryStatus.CANCELED])
        )
        if location_id is not None:
            del_query = del_query.filter(Delivery.location_id == location_id)
        elif warehouse_id is not None:
            del_query = del_query.join(Location, Delivery.location_id == Location.id).filter(
                Location.warehouse_id == warehouse_id
            )
        pending_deliveries = del_query.count()

        # 5. Scheduled transfers count (exclude DONE and CANCELED)
        trf_query = db.query(Transfer).filter(
            Transfer.status.notin_([TransferStatus.DONE, TransferStatus.CANCELED])
        )
        if location_id is not None:
            trf_query = trf_query.filter(
                or_(
                    Transfer.source_location_id == location_id,
                    Transfer.destination_location_id == location_id,
                )
            )
        elif warehouse_id is not None:
            src_loc = aliased(Location)
            dest_loc = aliased(Location)
            trf_query = (
                trf_query.outerjoin(src_loc, Transfer.source_location_id == src_loc.id)
                .outerjoin(dest_loc, Transfer.destination_location_id == dest_loc.id)
                .filter(
                    or_(
                        src_loc.warehouse_id == warehouse_id,
                        dest_loc.warehouse_id == warehouse_id,
                    )
                )
            )
        scheduled_transfers = trf_query.count()

        return DashboardKPIResponse(
            total_products=total_products,
            low_stock_items=low_stock_count,
            out_of_stock_items=out_of_stock_count,
            pending_receipts=pending_receipts,
            pending_deliveries=pending_deliveries,
            scheduled_transfers=scheduled_transfers,
        )
