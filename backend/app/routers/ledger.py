from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware import get_current_active_user
from app.models.enums import LedgerTransactionType
from app.models.models import User
from app.schemas.ledger import MoveHistoryResponse, StockLedgerResponse
from app.services.ledger_service import LedgerService

router = APIRouter(tags=["Stock Ledger & Move History"])


@router.get(
    "/api/ledger",
    response_model=List[StockLedgerResponse],
    summary="Query audit stock ledger history with optional filtering and pagination",
)
def list_stock_ledger(
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    transaction_type: Optional[LedgerTransactionType] = Query(None, description="Filter by transaction type"),
    source_location_id: Optional[int] = Query(None, description="Filter by source location ID"),
    destination_location_id: Optional[int] = Query(None, description="Filter by destination location ID"),
    location_id: Optional[int] = Query(None, description="Filter by either source OR destination location ID"),
    warehouse_id: Optional[int] = Query(None, description="Filter by source OR destination location warehouse ID"),
    performed_by: Optional[int] = Query(None, description="Filter by performing user ID"),
    reference_id: Optional[str] = Query(None, description="Filter by document reference ID"),
    date_from: Optional[datetime] = Query(None, description="Filter by minimum timestamp"),
    date_to: Optional[datetime] = Query(None, description="Filter by maximum timestamp"),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Read-only query of full immutable StockLedger audit history."""
    return LedgerService.list_ledger_entries(
        db=db,
        product_id=product_id,
        transaction_type=transaction_type,
        source_location_id=source_location_id,
        destination_location_id=destination_location_id,
        location_id=location_id,
        warehouse_id=warehouse_id,
        performed_by=performed_by,
        reference_id=reference_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/api/ledger/{id}",
    response_model=StockLedgerResponse,
    summary="Get single stock ledger record by ID",
)
def get_stock_ledger(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve detailed single StockLedger audit entry."""
    return LedgerService.get_ledger_entry(db=db, ledger_id=id)


@router.get(
    "/api/move-history",
    response_model=List[MoveHistoryResponse],
    summary="Query stock movement history derived directly from StockLedger",
)
def list_move_history(
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    transaction_type: Optional[LedgerTransactionType] = Query(None, alias="type", description="Filter by movement type"),
    source_location_id: Optional[int] = Query(None, description="Filter by source location ID"),
    destination_location_id: Optional[int] = Query(None, description="Filter by destination location ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID (either side)"),
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse ID"),
    performed_by: Optional[int] = Query(None, description="Filter by performing user ID"),
    reference_id: Optional[str] = Query(None, alias="reference", description="Filter by reference ID"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Read-only movement history view derived dynamically from StockLedger records."""
    return LedgerService.list_move_history(
        db=db,
        product_id=product_id,
        transaction_type=transaction_type,
        source_location_id=source_location_id,
        destination_location_id=destination_location_id,
        location_id=location_id,
        warehouse_id=warehouse_id,
        performed_by=performed_by,
        reference_id=reference_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
