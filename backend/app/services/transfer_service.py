from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import LedgerTransactionType, TransferStatus
from app.models.models import Location, Product, Transfer, TransferItem, User
from app.schemas.transfer import (
    TransferCreate,
    TransferItemResponse,
    TransferResponse,
    TransferUpdate,
)
from app.services.inventory_service import (
    InventoryError,
    InventoryService,
)


class TransferService:

    @classmethod
    def generate_transfer_number(cls, db: Session) -> str:
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"TRF-{today_str}-"
        last_transfer = (
            db.query(Transfer)
            .filter(Transfer.transfer_number.like(f"{prefix}%"))
            .order_by(Transfer.id.desc())
            .first()
        )
        if not last_transfer:
            count = 1
        else:
            try:
                suffix = last_transfer.transfer_number.split("-")[-1]
                count = int(suffix) + 1
            except (ValueError, IndexError):
                count = db.query(Transfer).count() + 1

        candidate = f"{prefix}{count:04d}"
        while db.query(Transfer).filter(Transfer.transfer_number == candidate).first():
            count += 1
            candidate = f"{prefix}{count:04d}"
        return candidate

    @classmethod
    def build_transfer_response(cls, transfer: Transfer) -> TransferResponse:
        items_res = []
        for item in transfer.items:
            items_res.append(
                TransferItemResponse(
                    id=item.id,
                    transfer_id=item.transfer_id,
                    product_id=item.product_id,
                    product_name=item.product.name if item.product else None,
                    sku=item.product.sku if item.product else None,
                    quantity=item.quantity,
                )
            )

        src_loc_name = transfer.source_location.name if transfer.source_location else None
        src_wh_id = transfer.source_location.warehouse_id if transfer.source_location else None
        src_wh_name = (
            transfer.source_location.warehouse.name
            if transfer.source_location and transfer.source_location.warehouse
            else None
        )

        dest_loc_name = transfer.destination_location.name if transfer.destination_location else None
        dest_wh_id = transfer.destination_location.warehouse_id if transfer.destination_location else None
        dest_wh_name = (
            transfer.destination_location.warehouse.name
            if transfer.destination_location and transfer.destination_location.warehouse
            else None
        )

        return TransferResponse(
            id=transfer.id,
            transfer_number=transfer.transfer_number,
            source_location_id=transfer.source_location_id,
            source_location_name=src_loc_name,
            source_warehouse_id=src_wh_id,
            source_warehouse_name=src_wh_name,
            destination_location_id=transfer.destination_location_id,
            destination_location_name=dest_loc_name,
            destination_warehouse_id=dest_wh_id,
            destination_warehouse_name=dest_wh_name,
            status=transfer.status.value if isinstance(transfer.status, TransferStatus) else str(transfer.status),
            created_by=transfer.created_by,
            created_at=transfer.created_at,
            updated_at=transfer.updated_at,
            items=items_res,
        )

    @classmethod
    def create_transfer(
        cls, db: Session, payload: TransferCreate, current_user: User
    ) -> TransferResponse:
        if payload.source_location_id == payload.destination_location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination locations cannot be identical.",
            )

        # Validate source location and warehouse
        src_loc = db.query(Location).filter(Location.id == payload.source_location_id).first()
        if not src_loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source location with ID {payload.source_location_id} not found",
            )
        if not src_loc.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source location with ID {payload.source_location_id} is inactive",
            )
        if not src_loc.warehouse or not src_loc.warehouse.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse associated with source location {payload.source_location_id} is inactive",
            )

        # Validate destination location and warehouse
        dest_loc = db.query(Location).filter(Location.id == payload.destination_location_id).first()
        if not dest_loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destination location with ID {payload.destination_location_id} not found",
            )
        if not dest_loc.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Destination location with ID {payload.destination_location_id} is inactive",
            )
        if not dest_loc.warehouse or not dest_loc.warehouse.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse associated with destination location {payload.destination_location_id} is inactive",
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
                transfer_number = cls.generate_transfer_number(db)

                transfer = Transfer(
                    transfer_number=transfer_number,
                    source_location_id=payload.source_location_id,
                    destination_location_id=payload.destination_location_id,
                    status=TransferStatus.DRAFT,
                    created_by=current_user.id,
                )
                db.add(transfer)
                db.flush()

                for item in payload.items:
                    trf_item = TransferItem(
                        transfer_id=transfer.id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                    )
                    db.add(trf_item)

                db.commit()
                db.refresh(transfer)
                return cls.build_transfer_response(transfer)
            except IntegrityError as e:
                db.rollback()
                err_str = str(e.orig).lower() if hasattr(e, "orig") and e.orig else str(e).lower()
                is_num_collision = "transfer_number" in err_str
                if is_num_collision and attempt < max_attempts - 1:
                    continue
                elif is_num_collision:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Transfer number collision occurred. Please try again.",
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
                    detail="Failed to create transfer document.",
                )

    @classmethod
    def get_transfer(cls, db: Session, transfer_id: int) -> TransferResponse:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transfer with ID {transfer_id} not found",
            )
        return cls.build_transfer_response(transfer)

    @classmethod
    def list_transfers(
        cls,
        db: Session,
        status_filter: Optional[TransferStatus] = None,
        source_location_id: Optional[int] = None,
        destination_location_id: Optional[int] = None,
        source_warehouse_id: Optional[int] = None,
        destination_warehouse_id: Optional[int] = None,
        search: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> List[TransferResponse]:
        query = db.query(Transfer)

        if status_filter:
            query = query.filter(Transfer.status == status_filter)

        if source_location_id:
            query = query.filter(Transfer.source_location_id == source_location_id)

        if destination_location_id:
            query = query.filter(Transfer.destination_location_id == destination_location_id)

        if source_warehouse_id:
            src_loc_alias = Location
            query = query.join(src_loc_alias, Transfer.source_location_id == src_loc_alias.id).filter(
                src_loc_alias.warehouse_id == source_warehouse_id
            )

        if destination_warehouse_id:
            dest_loc_alias = Location
            query = query.join(dest_loc_alias, Transfer.destination_location_id == dest_loc_alias.id).filter(
                dest_loc_alias.warehouse_id == destination_warehouse_id
            )

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(Transfer.transfer_number.ilike(term))

        if created_by:
            query = query.filter(Transfer.created_by == created_by)

        transfers = query.order_by(Transfer.created_at.desc(), Transfer.id.desc()).all()
        return [cls.build_transfer_response(t) for t in transfers]

    @classmethod
    def update_transfer(
        cls, db: Session, transfer_id: int, payload: TransferUpdate
    ) -> TransferResponse:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transfer with ID {transfer_id} not found",
            )

        if transfer.status in (TransferStatus.DONE, TransferStatus.CANCELED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transfer with status '{transfer.status.value}' cannot be updated",
            )

        if payload.status is not None:
            if payload.status in (TransferStatus.DONE, TransferStatus.CANCELED):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Direct status change to DONE or CANCELED is not allowed via PATCH. Use /validate or /cancel.",
                )

            allowed_transitions = {
                TransferStatus.DRAFT: {TransferStatus.WAITING, TransferStatus.IN_TRANSIT},
                TransferStatus.WAITING: {TransferStatus.IN_TRANSIT},
                TransferStatus.IN_TRANSIT: set(),
            }
            if payload.status != transfer.status:
                allowed = allowed_transitions.get(transfer.status, set())
                if payload.status not in allowed:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Status transition from '{transfer.status.value}' to '{payload.status.value}' is not allowed via PATCH",
                    )
            transfer.status = payload.status

        new_src_id = payload.source_location_id if payload.source_location_id is not None else transfer.source_location_id
        new_dest_id = payload.destination_location_id if payload.destination_location_id is not None else transfer.destination_location_id

        if new_src_id == new_dest_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination locations cannot be identical.",
            )

        if payload.source_location_id is not None and payload.source_location_id != transfer.source_location_id:
            src_loc = db.query(Location).filter(Location.id == payload.source_location_id).first()
            if not src_loc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Source location with ID {payload.source_location_id} not found",
                )
            if not src_loc.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Source location with ID {payload.source_location_id} is inactive",
                )
            if not src_loc.warehouse or not src_loc.warehouse.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Warehouse associated with source location {payload.source_location_id} is inactive",
                )
            transfer.source_location_id = payload.source_location_id

        if payload.destination_location_id is not None and payload.destination_location_id != transfer.destination_location_id:
            dest_loc = db.query(Location).filter(Location.id == payload.destination_location_id).first()
            if not dest_loc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Destination location with ID {payload.destination_location_id} not found",
                )
            if not dest_loc.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Destination location with ID {payload.destination_location_id} is inactive",
                )
            if not dest_loc.warehouse or not dest_loc.warehouse.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Warehouse associated with destination location {payload.destination_location_id} is inactive",
                )
            transfer.destination_location_id = payload.destination_location_id

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
            db.query(TransferItem).filter(TransferItem.transfer_id == transfer.id).delete()
            db.flush()

            # Insert new items
            for item in payload.items:
                trf_item = TransferItem(
                    transfer_id=transfer.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                )
                db.add(trf_item)

        try:
            db.commit()
            db.refresh(transfer)
            return cls.build_transfer_response(transfer)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update transfer.",
            )

    @classmethod
    def validate_transfer(
        cls, db: Session, transfer_id: int, current_user: User
    ) -> TransferResponse:
        # Load transfer with explicit row-level FOR UPDATE lock for database concurrency
        transfer = (
            db.query(Transfer)
            .filter(Transfer.id == transfer_id)
            .with_for_update()
            .first()
        )
        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transfer with ID {transfer_id} not found",
            )

        if transfer.status == TransferStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer has already been validated",
            )

        if transfer.status == TransferStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Canceled transfer cannot be validated",
            )

        if transfer.status != TransferStatus.IN_TRANSIT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transfer status must be IN_TRANSIT to validate, current status is '{transfer.status.value}'",
            )

        if transfer.source_location_id == transfer.destination_location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination locations cannot be identical.",
            )

        # Verify source location and warehouse remain active
        src_loc = db.query(Location).filter(Location.id == transfer.source_location_id).first()
        if not src_loc or not src_loc.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source location {transfer.source_location_id} is inactive or does not exist",
            )
        if not src_loc.warehouse or not src_loc.warehouse.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse associated with source location {transfer.source_location_id} is inactive",
            )

        # Verify destination location and warehouse remain active
        dest_loc = db.query(Location).filter(Location.id == transfer.destination_location_id).first()
        if not dest_loc or not dest_loc.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Destination location {transfer.destination_location_id} is inactive or does not exist",
            )
        if not dest_loc.warehouse or not dest_loc.warehouse.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse associated with destination location {transfer.destination_location_id} is inactive",
            )

        # Verify all products in items remain active and quantities > 0
        if not transfer.items or len(transfer.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer must contain at least one item to validate",
            )

        seen_products = set()
        for item in transfer.items:
            if item.product_id in seen_products:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate product_id {item.product_id} in transfer items is not allowed.",
                )
            seen_products.add(item.product_id)

            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product or not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product {item.product_id} in transfer is inactive or missing",
                )
            if item.quantity <= Decimal("0.0000"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transfer item quantity for product {item.product_id} must be greater than zero",
                )

        # Execute stock transfers via InventoryService within single transaction
        try:
            for item in transfer.items:
                InventoryService.transfer_stock(
                    db=db,
                    product_id=item.product_id,
                    source_location_id=transfer.source_location_id,
                    destination_location_id=transfer.destination_location_id,
                    quantity=item.quantity,
                    reference_id=str(transfer.id),
                    performed_by=current_user.id,
                    reason=f"Transfer {transfer.transfer_number} validation",
                )

            transfer.status = TransferStatus.DONE
            db.commit()
            db.refresh(transfer)
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
                detail="Failed to validate transfer.",
            )

        return cls.build_transfer_response(transfer)

    @classmethod
    def cancel_transfer(cls, db: Session, transfer_id: int) -> TransferResponse:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transfer with ID {transfer_id} not found",
            )

        if transfer.status == TransferStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a validated (DONE) transfer",
            )

        if transfer.status == TransferStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer is already canceled",
            )

        try:
            transfer.status = TransferStatus.CANCELED
            db.commit()
            db.refresh(transfer)
            return cls.build_transfer_response(transfer)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel transfer.",
            )
