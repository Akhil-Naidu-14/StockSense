from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased

from app.models.enums import LedgerTransactionType
from app.models.models import Location, StockLedger
from app.schemas.ledger import MoveHistoryResponse, StockLedgerResponse


class LedgerService:

    @classmethod
    def build_ledger_response(cls, entry: StockLedger) -> StockLedgerResponse:
        prod_name = entry.product.name if entry.product else None
        sku = entry.product.sku if entry.product else None

        src_name = entry.source_location.name if entry.source_location else None
        src_code = entry.source_location.code if entry.source_location else None

        dest_name = entry.destination_location.name if entry.destination_location else None
        dest_code = entry.destination_location.code if entry.destination_location else None

        user_name = entry.performer.name if entry.performer else None
        user_email = entry.performer.email if entry.performer else None

        return StockLedgerResponse(
            id=entry.id,
            timestamp=entry.timestamp,
            product_id=entry.product_id,
            product_name=prod_name,
            sku=sku,
            transaction_type=entry.transaction_type.value if isinstance(entry.transaction_type, LedgerTransactionType) else str(entry.transaction_type),
            quantity_before=entry.quantity_before,
            quantity_change=entry.quantity_change,
            quantity_after=entry.quantity_after,
            source_location_id=entry.source_location_id,
            source_location_name=src_name,
            source_location_code=src_code,
            destination_location_id=entry.destination_location_id,
            destination_location_name=dest_name,
            destination_location_code=dest_code,
            performed_by=entry.performed_by,
            performed_by_name=user_name,
            performed_by_email=user_email,
            reference_id=entry.reference_id,
            reason=entry.reason,
        )

    @classmethod
    def build_move_history_response(cls, entry: StockLedger) -> MoveHistoryResponse:
        prod_name = entry.product.name if entry.product else None
        sku = entry.product.sku if entry.product else None

        src_desc = entry.source_location.name if entry.source_location else None
        dest_desc = entry.destination_location.name if entry.destination_location else None

        user_desc = entry.performer.name or entry.performer.email if entry.performer else None

        # Quantity calculation per movement type
        qty = entry.quantity_change
        if entry.transaction_type in (LedgerTransactionType.RECEIPT, LedgerTransactionType.INITIAL_STOCK):
            qty = abs(entry.quantity_change)
        elif entry.transaction_type == LedgerTransactionType.DELIVERY:
            qty = -abs(entry.quantity_change)
        elif entry.transaction_type == LedgerTransactionType.ADJUSTMENT:
            qty = entry.quantity_change
        elif entry.transaction_type == LedgerTransactionType.TRANSFER:
            qty = abs(entry.quantity_change)

        return MoveHistoryResponse(
            id=entry.id,
            date=entry.timestamp,
            product=prod_name,
            product_sku=sku,
            product_id=entry.product_id,
            type=entry.transaction_type.value if isinstance(entry.transaction_type, LedgerTransactionType) else str(entry.transaction_type),
            source=src_desc,
            source_location_id=entry.source_location_id,
            destination=dest_desc,
            destination_location_id=entry.destination_location_id,
            quantity=qty,
            user=user_desc,
            performed_by=entry.performed_by,
            reference=entry.reference_id,
            reason=entry.reason,
        )

    @classmethod
    def list_ledger_entries(
        cls,
        db: Session,
        product_id: Optional[int] = None,
        transaction_type: Optional[LedgerTransactionType] = None,
        source_location_id: Optional[int] = None,
        destination_location_id: Optional[int] = None,
        location_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        performed_by: Optional[int] = None,
        reference_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[StockLedgerResponse]:
        query = db.query(StockLedger)

        if product_id is not None:
            query = query.filter(StockLedger.product_id == product_id)

        if transaction_type is not None:
            query = query.filter(StockLedger.transaction_type == transaction_type)

        if source_location_id is not None:
            query = query.filter(StockLedger.source_location_id == source_location_id)

        if destination_location_id is not None:
            query = query.filter(StockLedger.destination_location_id == destination_location_id)

        if location_id is not None:
            query = query.filter(
                or_(
                    StockLedger.source_location_id == location_id,
                    StockLedger.destination_location_id == location_id,
                )
            )

        if warehouse_id is not None:
            src_loc = aliased(Location)
            dest_loc = aliased(Location)
            query = (
                query.outerjoin(src_loc, StockLedger.source_location_id == src_loc.id)
                .outerjoin(dest_loc, StockLedger.destination_location_id == dest_loc.id)
                .filter(
                    or_(
                        src_loc.warehouse_id == warehouse_id,
                        dest_loc.warehouse_id == warehouse_id,
                    )
                )
            )

        if performed_by is not None:
            query = query.filter(StockLedger.performed_by == performed_by)

        if reference_id is not None:
            query = query.filter(StockLedger.reference_id == reference_id)

        if date_from is not None:
            query = query.filter(StockLedger.timestamp >= date_from)

        if date_to is not None:
            query = query.filter(StockLedger.timestamp <= date_to)

        safe_limit = min(max(1, limit), 500)
        safe_offset = max(0, offset)

        entries = (
            query.order_by(StockLedger.timestamp.desc(), StockLedger.id.desc())
            .offset(safe_offset)
            .limit(safe_limit)
            .all()
        )
        return [cls.build_ledger_response(e) for e in entries]

    @classmethod
    def get_ledger_entry(cls, db: Session, ledger_id: int) -> StockLedgerResponse:
        entry = db.query(StockLedger).filter(StockLedger.id == ledger_id).first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock ledger entry with ID {ledger_id} not found",
            )
        return cls.build_ledger_response(entry)

    @classmethod
    def list_move_history(
        cls,
        db: Session,
        product_id: Optional[int] = None,
        transaction_type: Optional[LedgerTransactionType] = None,
        source_location_id: Optional[int] = None,
        destination_location_id: Optional[int] = None,
        location_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        performed_by: Optional[int] = None,
        reference_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MoveHistoryResponse]:
        query = db.query(StockLedger)

        if product_id is not None:
            query = query.filter(StockLedger.product_id == product_id)

        if transaction_type is not None:
            query = query.filter(StockLedger.transaction_type == transaction_type)

        if source_location_id is not None:
            query = query.filter(StockLedger.source_location_id == source_location_id)

        if destination_location_id is not None:
            query = query.filter(StockLedger.destination_location_id == destination_location_id)

        if location_id is not None:
            query = query.filter(
                or_(
                    StockLedger.source_location_id == location_id,
                    StockLedger.destination_location_id == location_id,
                )
            )

        if warehouse_id is not None:
            src_loc = aliased(Location)
            dest_loc = aliased(Location)
            query = (
                query.outerjoin(src_loc, StockLedger.source_location_id == src_loc.id)
                .outerjoin(dest_loc, StockLedger.destination_location_id == dest_loc.id)
                .filter(
                    or_(
                        src_loc.warehouse_id == warehouse_id,
                        dest_loc.warehouse_id == warehouse_id,
                    )
                )
            )

        if performed_by is not None:
            query = query.filter(StockLedger.performed_by == performed_by)

        if reference_id is not None:
            query = query.filter(StockLedger.reference_id == reference_id)

        if date_from is not None:
            query = query.filter(StockLedger.timestamp >= date_from)

        if date_to is not None:
            query = query.filter(StockLedger.timestamp <= date_to)

        safe_limit = min(max(1, limit), 500)
        safe_offset = max(0, offset)

        entries = (
            query.order_by(StockLedger.timestamp.desc(), StockLedger.id.desc())
            .offset(safe_offset)
            .limit(safe_limit)
            .all()
        )
        return [cls.build_move_history_response(e) for e in entries]
