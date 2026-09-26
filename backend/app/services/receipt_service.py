from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import LedgerTransactionType, ReceiptStatus
from app.models.models import Location, Product, Receipt, ReceiptItem, User
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptItemResponse,
    ReceiptResponse,
    ReceiptUpdate,
)
from app.services.inventory_service import (
    InventoryError,
    InventoryService,
)


class ReceiptService:

    @classmethod
    def generate_receipt_number(cls, db: Session) -> str:
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"RCV-{today_str}-"
        last_receipt = (
            db.query(Receipt)
            .filter(Receipt.receipt_number.like(f"{prefix}%"))
            .order_by(Receipt.id.desc())
            .first()
        )
        if not last_receipt:
            count = 1
        else:
            try:
                suffix = last_receipt.receipt_number.split("-")[-1]
                count = int(suffix) + 1
            except (ValueError, IndexError):
                count = db.query(Receipt).count() + 1

        candidate = f"{prefix}{count:04d}"
        while db.query(Receipt).filter(Receipt.receipt_number == candidate).first():
            count += 1
            candidate = f"{prefix}{count:04d}"
        return candidate

    @classmethod
    def build_receipt_response(cls, receipt: Receipt) -> ReceiptResponse:
        items_res = []
        for item in receipt.items:
            items_res.append(
                ReceiptItemResponse(
                    id=item.id,
                    receipt_id=item.receipt_id,
                    product_id=item.product_id,
                    product_name=item.product.name if item.product else None,
                    sku=item.product.sku if item.product else None,
                    quantity=item.quantity,
                    received_quantity=item.received_quantity,
                )
            )

        loc_name = receipt.location.name if receipt.location else None
        wh_id = receipt.location.warehouse_id if receipt.location else None
        wh_name = (
            receipt.location.warehouse.name
            if receipt.location and receipt.location.warehouse
            else None
        )

        return ReceiptResponse(
            id=receipt.id,
            receipt_number=receipt.receipt_number,
            supplier=receipt.supplier,
            location_id=receipt.location_id,
            location_name=loc_name,
            warehouse_id=wh_id,
            warehouse_name=wh_name,
            status=receipt.status.value if isinstance(receipt.status, ReceiptStatus) else str(receipt.status),
            created_by=receipt.created_by,
            created_at=receipt.created_at,
            updated_at=receipt.updated_at,
            items=items_res,
        )

    @classmethod
    def create_receipt(
        cls, db: Session, payload: ReceiptCreate, current_user: User
    ) -> ReceiptResponse:
        # Validate location
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
                receipt_number = cls.generate_receipt_number(db)

                receipt = Receipt(
                    receipt_number=receipt_number,
                    supplier=payload.supplier,
                    location_id=payload.location_id,
                    status=ReceiptStatus.DRAFT,
                    created_by=current_user.id,
                )
                db.add(receipt)
                db.flush()

                for item in payload.items:
                    rec_item = ReceiptItem(
                        receipt_id=receipt.id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        received_quantity=item.received_quantity
                        if item.received_quantity is not None
                        else item.quantity,
                    )
                    db.add(rec_item)

                db.commit()
                db.refresh(receipt)
                return cls.build_receipt_response(receipt)
            except IntegrityError as e:
                db.rollback()
                err_str = str(e.orig).lower() if hasattr(e, "orig") and e.orig else str(e).lower()
                is_receipt_num_collision = "receipt_number" in err_str
                if is_receipt_num_collision and attempt < max_attempts - 1:
                    continue
                elif is_receipt_num_collision:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Receipt number collision occurred. Please try again.",
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
                    detail="Failed to create receipt document.",
                )

    @classmethod
    def get_receipt(cls, db: Session, receipt_id: int) -> ReceiptResponse:
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receipt with ID {receipt_id} not found",
            )
        return cls.build_receipt_response(receipt)

    @classmethod
    def list_receipts(
        cls,
        db: Session,
        status_filter: Optional[ReceiptStatus] = None,
        location_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        supplier: Optional[str] = None,
        search: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> List[ReceiptResponse]:
        query = db.query(Receipt)

        if status_filter:
            query = query.filter(Receipt.status == status_filter)

        if location_id:
            query = query.filter(Receipt.location_id == location_id)

        if warehouse_id:
            query = query.join(Location, Receipt.location_id == Location.id).filter(
                Location.warehouse_id == warehouse_id
            )

        if supplier:
            query = query.filter(Receipt.supplier.ilike(f"%{supplier.strip()}%"))

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Receipt.receipt_number.ilike(term),
                    Receipt.supplier.ilike(term),
                )
            )

        if created_by:
            query = query.filter(Receipt.created_by == created_by)

        receipts = query.order_by(Receipt.created_at.desc(), Receipt.id.desc()).all()
        return [cls.build_receipt_response(r) for r in receipts]

    @classmethod
    def update_receipt(
        cls, db: Session, receipt_id: int, payload: ReceiptUpdate
    ) -> ReceiptResponse:
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receipt with ID {receipt_id} not found",
            )

        if receipt.status != ReceiptStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Receipt with status '{receipt.status.value}' cannot be updated",
            )

        if payload.location_id is not None and payload.location_id != receipt.location_id:
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
            receipt.location_id = payload.location_id

        if payload.supplier is not None:
            receipt.supplier = payload.supplier

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
            db.query(ReceiptItem).filter(ReceiptItem.receipt_id == receipt.id).delete()
            db.flush()

            # Insert new items
            for item in payload.items:
                rec_item = ReceiptItem(
                    receipt_id=receipt.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    received_quantity=item.received_quantity
                    if item.received_quantity is not None
                    else item.quantity,
                )
                db.add(rec_item)

        try:
            db.commit()
            db.refresh(receipt)
            return cls.build_receipt_response(receipt)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update receipt.",
            )

    @classmethod
    def validate_receipt(
        cls, db: Session, receipt_id: int, current_user: User
    ) -> ReceiptResponse:
        # Load receipt with explicit row-level FOR UPDATE lock for database concurrency
        receipt = (
            db.query(Receipt)
            .filter(Receipt.id == receipt_id)
            .with_for_update()
            .first()
        )
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receipt with ID {receipt_id} not found",
            )

        if receipt.status in (ReceiptStatus.DONE, ReceiptStatus.RECEIVED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receipt has already been validated",
            )

        if receipt.status == ReceiptStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Canceled receipt cannot be validated",
            )

        if receipt.status != ReceiptStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Receipt in status '{receipt.status.value}' cannot be validated",
            )

        # Verify destination location and warehouse remain active
        location = db.query(Location).filter(Location.id == receipt.location_id).first()
        if not location or not location.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Destination location {receipt.location_id} is inactive or does not exist",
            )
        if not location.warehouse or not location.warehouse.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse associated with location {receipt.location_id} is inactive",
            )

        # Verify all products in items remain active
        has_positive_received = False
        for item in receipt.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product or not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product {item.product_id} in receipt is inactive or missing",
                )
            if item.received_quantity > Decimal("0.0000"):
                has_positive_received = True

        if not has_positive_received:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one item must have a received_quantity > 0 to validate receipt",
            )

        # Execute stock increases within single transaction
        try:
            for item in receipt.items:
                if item.received_quantity > Decimal("0.0000"):
                    InventoryService.increase_stock(
                        db=db,
                        product_id=item.product_id,
                        location_id=receipt.location_id,
                        quantity=item.received_quantity,
                        transaction_type=LedgerTransactionType.RECEIPT,
                        reference_id=str(receipt.id),
                        performed_by=current_user.id,
                        reason=f"Receipt {receipt.receipt_number} validation",
                    )

            receipt.status = ReceiptStatus.DONE
            db.commit()
            db.refresh(receipt)
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
                detail="Failed to validate receipt.",
            )

        return cls.build_receipt_response(receipt)

    @classmethod
    def cancel_receipt(cls, db: Session, receipt_id: int) -> ReceiptResponse:
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receipt with ID {receipt_id} not found",
            )

        if receipt.status in (ReceiptStatus.DONE, ReceiptStatus.RECEIVED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a validated (DONE) receipt",
            )

        if receipt.status == ReceiptStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receipt is already canceled",
            )

        receipt.status = ReceiptStatus.CANCELED
        db.commit()
        db.refresh(receipt)
        return cls.build_receipt_response(receipt)
