from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import DeliveryStatus, LedgerTransactionType
from app.models.models import Delivery, DeliveryItem, Location, Product, User
from app.schemas.delivery import (
    DeliveryCreate,
    DeliveryItemResponse,
    DeliveryResponse,
    DeliveryUpdate,
)
from app.services.inventory_service import (
    InventoryError,
    InventoryService,
)


class DeliveryService:

    @classmethod
    def generate_delivery_number(cls, db: Session) -> str:
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"DLV-{today_str}-"
        last_delivery = (
            db.query(Delivery)
            .filter(Delivery.delivery_number.like(f"{prefix}%"))
            .order_by(Delivery.id.desc())
            .first()
        )
        if not last_delivery:
            count = 1
        else:
            try:
                suffix = last_delivery.delivery_number.split("-")[-1]
                count = int(suffix) + 1
            except (ValueError, IndexError):
                count = db.query(Delivery).count() + 1

        candidate = f"{prefix}{count:04d}"
        while db.query(Delivery).filter(Delivery.delivery_number == candidate).first():
            count += 1
            candidate = f"{prefix}{count:04d}"
        return candidate

    @classmethod
    def build_delivery_response(cls, delivery: Delivery) -> DeliveryResponse:
        items_res = []
        for item in delivery.items:
            items_res.append(
                DeliveryItemResponse(
                    id=item.id,
                    delivery_id=item.delivery_id,
                    product_id=item.product_id,
                    product_name=item.product.name if item.product else None,
                    sku=item.product.sku if item.product else None,
                    quantity=item.quantity,
                )
            )

        loc_name = delivery.location.name if delivery.location else None
        wh_id = delivery.location.warehouse_id if delivery.location else None
        wh_name = (
            delivery.location.warehouse.name
            if delivery.location and delivery.location.warehouse
            else None
        )

        return DeliveryResponse(
            id=delivery.id,
            delivery_number=delivery.delivery_number,
            customer_reference=delivery.customer_reference,
            location_id=delivery.location_id,
            location_name=loc_name,
            warehouse_id=wh_id,
            warehouse_name=wh_name,
            status=delivery.status.value if isinstance(delivery.status, DeliveryStatus) else str(delivery.status),
            created_by=delivery.created_by,
            created_at=delivery.created_at,
            updated_at=delivery.updated_at,
            items=items_res,
        )

    @classmethod
    def create_delivery(
        cls, db: Session, payload: DeliveryCreate, current_user: User
    ) -> DeliveryResponse:
        # Validate source location
        location = db.query(Location).filter(Location.id == payload.location_id).first()
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source location with ID {payload.location_id} not found",
            )
        if not location.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source location with ID {payload.location_id} is inactive",
            )
        if not location.warehouse or not location.warehouse.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse associated with source location {payload.location_id} is inactive",
            )

        # Validate products
        for item in payload.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item.product_id} not found",
                )
            if not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product with ID {item.product_id} is inactive",
                )

        # Collision-safe creation loop with full transaction boundary inside try block
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                delivery_number = cls.generate_delivery_number(db)

                delivery = Delivery(
                    delivery_number=delivery_number,
                    customer_reference=payload.customer_reference,
                    location_id=payload.location_id,
                    status=DeliveryStatus.DRAFT,
                    created_by=current_user.id,
                )
                db.add(delivery)
                db.flush()

                for item in payload.items:
                    del_item = DeliveryItem(
                        delivery_id=delivery.id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                    )
                    db.add(del_item)

                db.commit()
                db.refresh(delivery)
                return cls.build_delivery_response(delivery)
            except IntegrityError as e:
                db.rollback()
                err_str = str(e.orig).lower() if hasattr(e, "orig") and e.orig else str(e).lower()
                is_num_collision = "delivery_number" in err_str
                if is_num_collision and attempt < max_attempts - 1:
                    continue
                elif is_num_collision:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Delivery number collision occurred. Please try again.",
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Database integrity constraint violated.",
                    )
            except HTTPException:
                db.rollback()
                raise
            except Exception:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create delivery document.",
                )

    @classmethod
    def get_delivery(cls, db: Session, delivery_id: int) -> DeliveryResponse:
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery with ID {delivery_id} not found",
            )
        return cls.build_delivery_response(delivery)

    @classmethod
    def list_deliveries(
        cls,
        db: Session,
        status_filter: Optional[DeliveryStatus] = None,
        location_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        customer_reference: Optional[str] = None,
        search: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> List[DeliveryResponse]:
        query = db.query(Delivery)

        if status_filter:
            query = query.filter(Delivery.status == status_filter)

        if location_id:
            query = query.filter(Delivery.location_id == location_id)

        if warehouse_id:
            query = query.join(Location, Delivery.location_id == Location.id).filter(
                Location.warehouse_id == warehouse_id
            )

        if customer_reference:
            query = query.filter(Delivery.customer_reference.ilike(f"%{customer_reference.strip()}%"))

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Delivery.delivery_number.ilike(term),
                    Delivery.customer_reference.ilike(term),
                )
            )

        if created_by:
            query = query.filter(Delivery.created_by == created_by)

        deliveries = query.order_by(Delivery.created_at.desc(), Delivery.id.desc()).all()
        return [cls.build_delivery_response(d) for d in deliveries]

    @classmethod
    def update_delivery(
        cls, db: Session, delivery_id: int, payload: DeliveryUpdate
    ) -> DeliveryResponse:
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery with ID {delivery_id} not found",
            )

        if delivery.status in (DeliveryStatus.DONE, DeliveryStatus.CANCELED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Delivery with status '{delivery.status.value}' cannot be updated",
            )

        if payload.status is not None:
            if payload.status in (DeliveryStatus.DONE, DeliveryStatus.CANCELED):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Direct status change to DONE or CANCELED is not allowed via PATCH. Use /validate or /cancel.",
                )

            allowed_transitions = {
                DeliveryStatus.DRAFT: {DeliveryStatus.WAITING, DeliveryStatus.READY},
                DeliveryStatus.WAITING: {DeliveryStatus.READY},
                DeliveryStatus.READY: {DeliveryStatus.PICKED},
                DeliveryStatus.PICKED: {DeliveryStatus.PACKED},
                DeliveryStatus.PACKED: set(),
            }
            if payload.status != delivery.status:
                allowed = allowed_transitions.get(delivery.status, set())
                if payload.status not in allowed:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Status transition from '{delivery.status.value}' to '{payload.status.value}' is not allowed via PATCH",
                    )
            delivery.status = payload.status

        if payload.location_id is not None and payload.location_id != delivery.location_id:
            location = db.query(Location).filter(Location.id == payload.location_id).first()
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Source location with ID {payload.location_id} not found",
                )
            if not location.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Source location with ID {payload.location_id} is inactive",
                )
            if not location.warehouse or not location.warehouse.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Warehouse associated with source location {payload.location_id} is inactive",
                )
            delivery.location_id = payload.location_id

        if payload.customer_reference is not None:
            delivery.customer_reference = payload.customer_reference

        if payload.items is not None:
            for item in payload.items:
                product = db.query(Product).filter(Product.id == item.product_id).first()
                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product with ID {item.product_id} not found",
                    )
                if not product.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product with ID {item.product_id} is inactive",
                    )

            # Delete existing items
            db.query(DeliveryItem).filter(DeliveryItem.delivery_id == delivery.id).delete()
            db.flush()

            # Insert new items
            for item in payload.items:
                del_item = DeliveryItem(
                    delivery_id=delivery.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                )
                db.add(del_item)

        try:
            db.commit()
            db.refresh(delivery)
            return cls.build_delivery_response(delivery)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update delivery.",
            )

    @classmethod
    def validate_delivery(
        cls, db: Session, delivery_id: int, current_user: User
    ) -> DeliveryResponse:
        # Load delivery with explicit row-level FOR UPDATE lock for database concurrency
        delivery = (
            db.query(Delivery)
            .filter(Delivery.id == delivery_id)
            .with_for_update()
            .first()
        )
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery with ID {delivery_id} not found",
            )

        if delivery.status == DeliveryStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery has already been validated",
            )

        if delivery.status == DeliveryStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Canceled delivery cannot be validated",
            )

        if delivery.status != DeliveryStatus.PACKED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Delivery status must be PACKED to validate, current status is '{delivery.status.value}'",
            )

        # Verify source location and warehouse remain active
        location = db.query(Location).filter(Location.id == delivery.location_id).first()
        if not location or not location.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source location {delivery.location_id} is inactive or does not exist",
            )
        if not location.warehouse or not location.warehouse.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse associated with source location {delivery.location_id} is inactive",
            )

        # Verify all products in items remain active and quantities > 0
        if not delivery.items or len(delivery.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery must contain at least one item to validate",
            )

        for item in delivery.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product or not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product {item.product_id} in delivery is inactive or missing",
                )
            if item.quantity <= Decimal("0.0000"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Delivery item quantity for product {item.product_id} must be greater than zero",
                )

        # Execute stock deductions via InventoryService within single transaction
        try:
            for item in delivery.items:
                InventoryService.decrease_stock(
                    db=db,
                    product_id=item.product_id,
                    location_id=delivery.location_id,
                    quantity=item.quantity,
                    transaction_type=LedgerTransactionType.DELIVERY,
                    reference_id=str(delivery.id),
                    performed_by=current_user.id,
                    reason=f"Delivery {delivery.delivery_number} validation",
                )

            delivery.status = DeliveryStatus.DONE
            db.commit()
            db.refresh(delivery)
        except HTTPException:
            db.rollback()
            raise
        except InventoryError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to validate delivery.",
            )

        return cls.build_delivery_response(delivery)

    @classmethod
    def cancel_delivery(cls, db: Session, delivery_id: int) -> DeliveryResponse:
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery with ID {delivery_id} not found",
            )

        if delivery.status == DeliveryStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a validated (DONE) delivery",
            )

        if delivery.status == DeliveryStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery is already canceled",
            )

        try:
            delivery.status = DeliveryStatus.CANCELED
            db.commit()
            db.refresh(delivery)
            return cls.build_delivery_response(delivery)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel delivery.",
            )
