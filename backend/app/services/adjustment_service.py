from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import AdjustmentStatus
from app.models.models import Adjustment, Location, Product, User
from app.schemas.adjustment import (
    AdjustmentCreate,
    AdjustmentResponse,
    AdjustmentUpdate,
)
from app.services.inventory_service import (
    InventoryError,
    InventoryService,
)


class AdjustmentService:

    @classmethod
    def build_adjustment_response(cls, adjustment: Adjustment) -> AdjustmentResponse:
        prod_name = adjustment.product.name if adjustment.product else None
        prod_sku = adjustment.product.sku if adjustment.product else None
        loc_name = adjustment.location.name if adjustment.location else None
        wh_id = adjustment.location.warehouse_id if adjustment.location else None
        wh_name = (
            adjustment.location.warehouse.name
            if adjustment.location and adjustment.location.warehouse
            else None
        )

        return AdjustmentResponse(
            id=adjustment.id,
            product_id=adjustment.product_id,
            product_name=prod_name,
            sku=prod_sku,
            location_id=adjustment.location_id,
            location_name=loc_name,
            warehouse_id=wh_id,
            warehouse_name=wh_name,
            system_quantity=adjustment.system_quantity,
            counted_quantity=adjustment.counted_quantity,
            difference=adjustment.difference,
            reason=adjustment.reason,
            status=adjustment.status.value if isinstance(adjustment.status, AdjustmentStatus) else str(adjustment.status),
            created_by=adjustment.created_by,
            created_at=adjustment.created_at,
        )

    @classmethod
    def create_adjustment(
        cls, db: Session, payload: AdjustmentCreate, current_user: User
    ) -> AdjustmentResponse:
        if payload.counted_quantity < Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Counted quantity cannot be negative.",
            )

        # Validate product active
        product = db.query(Product).filter(Product.id == payload.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {payload.product_id} not found",
            )
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with ID {payload.product_id} is inactive",
            )

        # Validate location and warehouse active
        location = db.query(Location).filter(Location.id == payload.location_id).first()
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location with ID {payload.location_id} not found",
            )
        if not location.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location with ID {payload.location_id} is inactive",
            )
        if not location.warehouse or not location.warehouse.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse associated with location {payload.location_id} is inactive",
            )

        # Capture current system quantity for draft display
        sys_qty = InventoryService.get_stock(db, payload.product_id, payload.location_id)
        diff = payload.counted_quantity - sys_qty

        adjustment = Adjustment(
            product_id=payload.product_id,
            location_id=payload.location_id,
            system_quantity=sys_qty,
            counted_quantity=payload.counted_quantity,
            difference=diff,
            reason=payload.reason,
            status=AdjustmentStatus.DRAFT,
            created_by=current_user.id,
        )

        try:
            db.add(adjustment)
            db.commit()
            db.refresh(adjustment)
            return cls.build_adjustment_response(adjustment)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database integrity constraint violated while creating adjustment.",
            )
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create adjustment document.",
            )

    @classmethod
    def get_adjustment(cls, db: Session, adjustment_id: int) -> AdjustmentResponse:
        adjustment = db.query(Adjustment).filter(Adjustment.id == adjustment_id).first()
        if not adjustment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adjustment with ID {adjustment_id} not found",
            )
        return cls.build_adjustment_response(adjustment)

    @classmethod
    def list_adjustments(
        cls,
        db: Session,
        status_filter: Optional[AdjustmentStatus] = None,
        product_id: Optional[int] = None,
        location_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        search: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> List[AdjustmentResponse]:
        query = db.query(Adjustment)

        if status_filter:
            query = query.filter(Adjustment.status == status_filter)

        if product_id:
            query = query.filter(Adjustment.product_id == product_id)

        if location_id:
            query = query.filter(Adjustment.location_id == location_id)

        if warehouse_id:
            query = query.join(Location, Adjustment.location_id == Location.id).filter(
                Location.warehouse_id == warehouse_id
            )

        if created_by:
            query = query.filter(Adjustment.created_by == created_by)

        if search:
            term = f"%{search.strip()}%"
            query = query.join(Product, Adjustment.product_id == Product.id).filter(
                or_(
                    Product.name.ilike(term),
                    Product.sku.ilike(term),
                    Adjustment.reason.ilike(term),
                )
            )

        adjustments = query.order_by(Adjustment.created_at.desc(), Adjustment.id.desc()).all()
        return [cls.build_adjustment_response(adj) for adj in adjustments]

    @classmethod
    def update_adjustment(
        cls, db: Session, adjustment_id: int, payload: AdjustmentUpdate
    ) -> AdjustmentResponse:
        adjustment = db.query(Adjustment).filter(Adjustment.id == adjustment_id).first()
        if not adjustment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adjustment with ID {adjustment_id} not found",
            )

        if adjustment.status in (AdjustmentStatus.DONE, AdjustmentStatus.CANCELED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Adjustment with status '{adjustment.status.value}' cannot be updated",
            )

        if payload.status is not None:
            if payload.status in (AdjustmentStatus.DONE, AdjustmentStatus.CANCELED):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Direct status change to DONE or CANCELED is not allowed via PATCH. Use /validate or /cancel.",
                )
            allowed_transitions = {
                AdjustmentStatus.DRAFT: {AdjustmentStatus.PENDING_APPROVAL, AdjustmentStatus.APPROVED},
                AdjustmentStatus.PENDING_APPROVAL: {AdjustmentStatus.APPROVED, AdjustmentStatus.REJECTED, AdjustmentStatus.DRAFT},
                AdjustmentStatus.APPROVED: {AdjustmentStatus.DRAFT},
                AdjustmentStatus.REJECTED: {AdjustmentStatus.DRAFT},
            }
            if payload.status != adjustment.status:
                allowed = allowed_transitions.get(adjustment.status, set())
                if payload.status not in allowed:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Status transition from '{adjustment.status.value}' to '{payload.status.value}' is not allowed via PATCH",
                    )
            adjustment.status = payload.status

        target_product_id = payload.product_id if payload.product_id is not None else adjustment.product_id
        target_location_id = payload.location_id if payload.location_id is not None else adjustment.location_id
        target_counted_qty = payload.counted_quantity if payload.counted_quantity is not None else adjustment.counted_quantity

        if payload.product_id is not None and payload.product_id != adjustment.product_id:
            product = db.query(Product).filter(Product.id == payload.product_id).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {payload.product_id} not found",
                )
            if not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product with ID {payload.product_id} is inactive",
                )
            adjustment.product_id = payload.product_id

        if payload.location_id is not None and payload.location_id != adjustment.location_id:
            location = db.query(Location).filter(Location.id == payload.location_id).first()
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Location with ID {payload.location_id} not found",
                )
            if not location.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Location with ID {payload.location_id} is inactive",
                )
            if not location.warehouse or not location.warehouse.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Warehouse associated with location {payload.location_id} is inactive",
                )
            adjustment.location_id = payload.location_id

        if payload.counted_quantity is not None:
            if payload.counted_quantity < Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Counted quantity cannot be negative.",
                )
            adjustment.counted_quantity = payload.counted_quantity

        if payload.reason is not None:
            adjustment.reason = payload.reason

        # Recalculate system_quantity and difference for display
        sys_qty = InventoryService.get_stock(db, target_product_id, target_location_id)
        adjustment.system_quantity = sys_qty
        adjustment.difference = target_counted_qty - sys_qty

        try:
            db.commit()
            db.refresh(adjustment)
            return cls.build_adjustment_response(adjustment)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update adjustment.",
            )

    @classmethod
    def validate_adjustment(
        cls, db: Session, adjustment_id: int, current_user: User
    ) -> AdjustmentResponse:
        # Load adjustment with explicit row-level FOR UPDATE lock for database concurrency
        adjustment = (
            db.query(Adjustment)
            .filter(Adjustment.id == adjustment_id)
            .with_for_update()
            .first()
        )
        if not adjustment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adjustment with ID {adjustment_id} not found",
            )

        if adjustment.status == AdjustmentStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adjustment has already been validated",
            )

        if adjustment.status == AdjustmentStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Canceled adjustment cannot be validated",
            )

        pre_validation_statuses = {
            AdjustmentStatus.DRAFT,
            AdjustmentStatus.PENDING_APPROVAL,
            AdjustmentStatus.APPROVED,
        }
        if adjustment.status not in pre_validation_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Adjustment with status '{adjustment.status.value}' cannot be validated",
            )

        if adjustment.counted_quantity < Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Counted quantity cannot be negative.",
            )

        # Revalidate active product
        product = db.query(Product).filter(Product.id == adjustment.product_id).first()
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {adjustment.product_id} in adjustment is inactive or missing",
            )

        # Revalidate active location and warehouse
        location = db.query(Location).filter(Location.id == adjustment.location_id).first()
        if not location or not location.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location {adjustment.location_id} in adjustment is inactive or missing",
            )
        if not location.warehouse or not location.warehouse.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse associated with location {adjustment.location_id} is inactive",
            )

        # Execute stock adjustment via InventoryService inside single transaction
        try:
            # Capture current system quantity BEFORE calling adjust_stock
            sys_qty_at_validation = InventoryService.get_stock(db, adjustment.product_id, adjustment.location_id)

            InventoryService.adjust_stock(
                db=db,
                product_id=adjustment.product_id,
                location_id=adjustment.location_id,
                counted_quantity=adjustment.counted_quantity,
                reference_id=str(adjustment.id),
                performed_by=current_user.id,
                reason=adjustment.reason or f"Adjustment {adjustment.id} validation",
            )

            adjustment.system_quantity = sys_qty_at_validation
            adjustment.difference = adjustment.counted_quantity - sys_qty_at_validation
            adjustment.status = AdjustmentStatus.DONE

            db.commit()
            db.refresh(adjustment)
            return cls.build_adjustment_response(adjustment)
        except HTTPException:
            db.rollback()
            raise
        except InventoryError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent stock operation conflict occurred during validation. Please try again.",
            )
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to validate adjustment.",
            )

    @classmethod
    def cancel_adjustment(cls, db: Session, adjustment_id: int) -> AdjustmentResponse:
        adjustment = db.query(Adjustment).filter(Adjustment.id == adjustment_id).first()
        if not adjustment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adjustment with ID {adjustment_id} not found",
            )

        if adjustment.status == AdjustmentStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a validated (DONE) adjustment",
            )

        if adjustment.status == AdjustmentStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adjustment is already canceled",
            )

        try:
            adjustment.status = AdjustmentStatus.CANCELED
            db.commit()
            db.refresh(adjustment)
            return cls.build_adjustment_response(adjustment)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel adjustment.",
            )
