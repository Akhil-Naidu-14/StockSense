"""
Centralized Inventory Service for StockSense.

ARCHITECTURAL RULE:
ALL stock-changing operations must execute through this InventoryService.
Routers and business document workflows must NEVER independently calculate or update stock.

This service serves as the single source of truth for:
- Current stock & available stock calculations
- Stock increases (Receipts, Initial Stock)
- Stock decreases (Deliveries, Waste)
- Stock transfers (Inter-location / Inter-warehouse)
- Stock adjustments (Physical inventory counts)
- Insufficient-stock validations against reserved quantities
- Stock ledger record creation
- Low-stock and out-of-stock evaluation
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple, Union
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import LedgerTransactionType
from app.models.models import Inventory, Location, Product, ReorderRule, StockLedger


# ============================================================================
# DOMAIN EXCEPTIONS
# ============================================================================

class InventoryError(Exception):
    """Base domain exception for inventory operations."""
    pass


class InvalidQuantityError(InventoryError):
    """Raised when an invalid quantity (e.g. <= 0 or negative) is supplied."""
    pass


class InvalidTransactionTypeError(InventoryError):
    """Raised when an invalid transaction type is supplied for a specific stock operation."""
    pass


class InsufficientStockError(InventoryError):
    """Raised when available stock is insufficient for a decrease or transfer operation."""
    pass


class InventoryNotFoundError(InventoryError):
    """Raised when an inventory row or record is not found."""
    pass


class InvalidTransferError(InventoryError):
    """Raised when a stock transfer configuration or state is invalid."""
    pass


class InvalidAdjustmentError(InventoryError):
    """Raised when a stock adjustment violates business constraints (e.g. below reserved quantity)."""
    pass


class ProductNotFoundError(InventoryError):
    """Raised when a product is missing or inactive."""
    pass


class LocationNotFoundError(InventoryError):
    """Raised when a location is missing or inactive."""
    pass


# ============================================================================
# INVENTORY SERVICE IMPLEMENTATION
# ============================================================================

class InventoryService:
    """Centralized domain service for all inventory state mutations and ledger history."""

    QUANTITY_FOUR_PLACES = Decimal("0.0001")

    @classmethod
    def _to_decimal(cls, val: Any) -> Decimal:
        """Convert input to Decimal and quantize to 4 decimal places (Numeric(12, 4))."""
        if isinstance(val, Decimal):
            d = val
        else:
            d = Decimal(str(val))
        return d.quantize(cls.QUANTITY_FOUR_PLACES, rounding=ROUND_HALF_UP)

    @classmethod
    def _validate_positive_quantity(cls, quantity: Any) -> Decimal:
        """Validate that quantity is strictly greater than 0."""
        dec_qty = cls._to_decimal(quantity)
        if dec_qty <= Decimal("0.0000"):
            raise InvalidQuantityError("Quantity must be greater than zero.")
        return dec_qty

    @classmethod
    def _validate_non_negative_quantity(cls, quantity: Any) -> Decimal:
        """Validate that quantity is non-negative (>= 0)."""
        dec_qty = cls._to_decimal(quantity)
        if dec_qty < Decimal("0.0000"):
            raise InvalidQuantityError("Quantity cannot be negative.")
        return dec_qty

    @classmethod
    def _get_active_product(cls, db: Session, product_id: int) -> Product:
        """Fetch active product or raise ProductNotFoundError."""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product or not product.is_active:
            raise ProductNotFoundError(f"Product with ID {product_id} was not found or is inactive.")
        return product

    @classmethod
    def _get_active_location(cls, db: Session, location_id: int) -> Location:
        """Fetch active location or raise LocationNotFoundError."""
        location = db.query(Location).filter(Location.id == location_id).first()
        if not location or not location.is_active:
            raise LocationNotFoundError(f"Location with ID {location_id} was not found or is inactive.")
        return location

    @classmethod
    def _get_or_create_inventory(
        cls, db: Session, product_id: int, location_id: int, lock: bool = True
    ) -> Inventory:
        """
        Fetch or create an Inventory row for (product_id, location_id).
        Uses row-level locking (FOR UPDATE) when requested.
        """
        cls._get_active_product(db, product_id)
        cls._get_active_location(db, location_id)

        query = db.query(Inventory).filter(
            Inventory.product_id == product_id,
            Inventory.location_id == location_id,
        )

        if lock:
            try:
                query = query.with_for_update()
            except Exception:
                # SQLite or dialect without row lock fallback
                pass

        inventory = query.first()

        if not inventory:
            inventory = Inventory(
                product_id=product_id,
                location_id=location_id,
                quantity=Decimal("0.0000"),
                reserved_quantity=Decimal("0.0000"),
            )
            db.add(inventory)
            db.flush()

        return inventory

    # ------------------------------------------------------------------------
    # READ / QUERY METHODS
    # ------------------------------------------------------------------------

    @classmethod
    def get_stock(cls, db: Session, product_id: int, location_id: int) -> Decimal:
        """Get current physical quantity for product at location."""
        inv = (
            db.query(Inventory)
            .filter(Inventory.product_id == product_id, Inventory.location_id == location_id)
            .first()
        )
        return inv.quantity if inv else Decimal("0.0000")

    @classmethod
    def get_available_stock(cls, db: Session, product_id: int, location_id: int) -> Decimal:
        """Get available stock (quantity - reserved_quantity) for product at location."""
        inv = (
            db.query(Inventory)
            .filter(Inventory.product_id == product_id, Inventory.location_id == location_id)
            .first()
        )
        if not inv:
            return Decimal("0.0000")
        return inv.quantity - inv.reserved_quantity

    # ------------------------------------------------------------------------
    # LEDGER CREATION
    # ------------------------------------------------------------------------

    @classmethod
    def create_ledger_entry(
        cls,
        db: Session,
        transaction_type: LedgerTransactionType,
        product_id: int,
        source_location_id: Optional[int],
        destination_location_id: Optional[int],
        quantity_before: Union[Decimal, str, float, int],
        quantity_change: Union[Decimal, str, float, int],
        quantity_after: Union[Decimal, str, float, int],
        reference_id: Optional[str] = None,
        performed_by: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> StockLedger:
        """Record an immutable stock movement entry in the StockLedger table."""
        ledger = StockLedger(
            transaction_type=transaction_type,
            product_id=product_id,
            source_location_id=source_location_id,
            destination_location_id=destination_location_id,
            quantity_before=cls._to_decimal(quantity_before),
            quantity_change=cls._to_decimal(quantity_change),
            quantity_after=cls._to_decimal(quantity_after),
            reference_id=reference_id,
            performed_by=performed_by,
            reason=reason,
        )
        db.add(ledger)
        db.flush()
        return ledger

    # ------------------------------------------------------------------------
    # MUTATION METHODS
    # ------------------------------------------------------------------------

    @classmethod
    def increase_stock(
        cls,
        db: Session,
        product_id: int,
        location_id: int,
        quantity: Union[Decimal, str, float, int],
        transaction_type: LedgerTransactionType = LedgerTransactionType.RECEIPT,
        reference_id: Optional[str] = None,
        performed_by: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Inventory:
        """
        Increase physical stock at a location.
        Enforces that transaction_type is RECEIPT or INITIAL_STOCK.
        Creates an Inventory record if none exists.
        Records a positive quantity_change in the StockLedger.
        """
        if transaction_type not in (LedgerTransactionType.RECEIPT, LedgerTransactionType.INITIAL_STOCK):
            raise InvalidTransactionTypeError(
                f"Invalid transaction type '{transaction_type}' for stock increase. Allowed: RECEIPT, INITIAL_STOCK."
            )

        dec_qty = cls._validate_positive_quantity(quantity)
        inventory = cls._get_or_create_inventory(db, product_id, location_id, lock=True)

        qty_before = inventory.quantity
        qty_after = qty_before + dec_qty
        inventory.quantity = qty_after

        cls.create_ledger_entry(
            db=db,
            transaction_type=transaction_type,
            product_id=product_id,
            source_location_id=None,
            destination_location_id=location_id,
            quantity_before=qty_before,
            quantity_change=dec_qty,
            quantity_after=qty_after,
            reference_id=reference_id,
            performed_by=performed_by,
            reason=reason,
        )

        db.flush()
        return inventory

    @classmethod
    def decrease_stock(
        cls,
        db: Session,
        product_id: int,
        location_id: int,
        quantity: Union[Decimal, str, float, int],
        transaction_type: LedgerTransactionType = LedgerTransactionType.DELIVERY,
        reference_id: Optional[str] = None,
        performed_by: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Inventory:
        """
        Decrease physical stock at a location.
        Enforces that transaction_type is DELIVERY.
        Validates against AVAILABLE stock (quantity - reserved_quantity).
        Records a negative quantity_change in the StockLedger.
        """
        if transaction_type != LedgerTransactionType.DELIVERY:
            raise InvalidTransactionTypeError(
                f"Invalid transaction type '{transaction_type}' for stock decrease. Allowed: DELIVERY."
            )

        dec_qty = cls._validate_positive_quantity(quantity)
        cls._get_active_product(db, product_id)
        cls._get_active_location(db, location_id)

        query = db.query(Inventory).filter(
            Inventory.product_id == product_id,
            Inventory.location_id == location_id,
        )
        try:
            query = query.with_for_update()
        except Exception:
            pass

        inventory = query.first()

        if not inventory:
            raise InsufficientStockError(
                f"Insufficient stock for product {product_id} at location {location_id}. "
                f"Requested: {dec_qty}, Available: 0.0000"
            )

        avail_qty = inventory.quantity - inventory.reserved_quantity
        if avail_qty < dec_qty:
            raise InsufficientStockError(
                f"Insufficient available stock for product {product_id} at location {location_id}. "
                f"Requested: {dec_qty}, Available: {avail_qty}"
            )

        qty_before = inventory.quantity
        qty_after = qty_before - dec_qty
        inventory.quantity = qty_after

        cls.create_ledger_entry(
            db=db,
            transaction_type=transaction_type,
            product_id=product_id,
            source_location_id=location_id,
            destination_location_id=None,
            quantity_before=qty_before,
            quantity_change=-dec_qty,
            quantity_after=qty_after,
            reference_id=reference_id,
            performed_by=performed_by,
            reason=reason,
        )

        db.flush()
        return inventory

    @classmethod
    def transfer_stock(
        cls,
        db: Session,
        product_id: int,
        source_location_id: int,
        destination_location_id: int,
        quantity: Union[Decimal, str, float, int],
        reference_id: Optional[str] = None,
        performed_by: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Tuple[Inventory, Inventory]:
        """
        Transfer stock from source location to destination location.
        Validates both source AND destination location active states.
        Validates source stock availability and preserves company-wide stock.
        Records a single TRANSFER ledger entry detailing the movement.
        """
        if source_location_id == destination_location_id:
            raise InvalidTransferError("Source and destination locations cannot be identical.")

        dec_qty = cls._validate_positive_quantity(quantity)
        cls._get_active_product(db, product_id)
        cls._get_active_location(db, source_location_id)
        cls._get_active_location(db, destination_location_id)

        # Retrieve source inventory with row lock
        src_query = db.query(Inventory).filter(
            Inventory.product_id == product_id,
            Inventory.location_id == source_location_id,
        )
        try:
            src_query = src_query.with_for_update()
        except Exception:
            pass

        source_inv = src_query.first()
        if not source_inv:
            raise InsufficientStockError(
                f"Insufficient stock for transfer at source location {source_location_id}. "
                f"Requested: {dec_qty}, Available: 0.0000"
            )

        src_avail = source_inv.quantity - source_inv.reserved_quantity
        if src_avail < dec_qty:
            raise InsufficientStockError(
                f"Insufficient available stock for transfer at source location {source_location_id}. "
                f"Requested: {dec_qty}, Available: {src_avail}"
            )

        # Retrieve or create destination inventory with row lock
        dest_inv = cls._get_or_create_inventory(
            db, product_id, destination_location_id, lock=True
        )

        src_before = source_inv.quantity
        src_after = src_before - dec_qty
        source_inv.quantity = src_after

        dest_before = dest_inv.quantity
        dest_after = dest_before + dec_qty
        dest_inv.quantity = dest_after

        cls.create_ledger_entry(
            db=db,
            transaction_type=LedgerTransactionType.TRANSFER,
            product_id=product_id,
            source_location_id=source_location_id,
            destination_location_id=destination_location_id,
            quantity_before=src_before,
            quantity_change=dec_qty,
            quantity_after=src_after,
            reference_id=reference_id,
            performed_by=performed_by,
            reason=reason,
        )

        db.flush()
        return source_inv, dest_inv

    @classmethod
    def adjust_stock(
        cls,
        db: Session,
        product_id: int,
        location_id: int,
        counted_quantity: Union[Decimal, str, float, int],
        reference_id: Optional[str] = None,
        performed_by: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Inventory:
        """
        Adjust stock at a location based on a physical count.
        Calculates signed difference = counted_quantity - system_quantity.
        Validates that counted_quantity >= reserved_quantity.
        Recording zero difference is retained as physical audit verification evidence.
        Records an ADJUSTMENT ledger entry with system_quantity, difference, and final counted_quantity.
        """
        dec_counted = cls._validate_non_negative_quantity(counted_quantity)
        inventory = cls._get_or_create_inventory(db, product_id, location_id, lock=True)

        system_qty = inventory.quantity
        diff = dec_counted - system_qty

        if dec_counted < inventory.reserved_quantity:
            raise InvalidAdjustmentError(
                f"Cannot adjust physical stock to {dec_counted} as it is below reserved quantity ({inventory.reserved_quantity})."
            )

        inventory.quantity = dec_counted

        cls.create_ledger_entry(
            db=db,
            transaction_type=LedgerTransactionType.ADJUSTMENT,
            product_id=product_id,
            source_location_id=location_id,
            destination_location_id=location_id,
            quantity_before=system_qty,
            quantity_change=diff,
            quantity_after=dec_counted,
            reference_id=reference_id,
            performed_by=performed_by,
            reason=reason,
        )

        db.flush()
        return inventory

    @classmethod
    def set_initial_stock(
        cls,
        db: Session,
        product_id: int,
        location_id: int,
        quantity: Union[Decimal, str, float, int],
        reference_id: Optional[str] = None,
        performed_by: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Inventory:
        """
        Initialize stock for a product at a location using transaction_type = INITIAL_STOCK.
        Safety Invariant: Rejects set_initial_stock if stock has already been initialized (quantity > 0).
        """
        existing_stock = cls.get_stock(db, product_id, location_id)
        if existing_stock > Decimal("0.0000"):
            raise InvalidAdjustmentError(
                f"Initial stock cannot be re-applied because stock already exists ({existing_stock}) "
                f"for product {product_id} at location {location_id}."
            )

        return cls.increase_stock(
            db=db,
            product_id=product_id,
            location_id=location_id,
            quantity=quantity,
            transaction_type=LedgerTransactionType.INITIAL_STOCK,
            reference_id=reference_id,
            performed_by=performed_by,
            reason=reason or "Initial Stock Setup",
        )

    # ------------------------------------------------------------------------
    # LOW-STOCK EVALUATION
    # ------------------------------------------------------------------------

    @classmethod
    def check_low_stock(
        cls, db: Session, product_id: int, location_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluate low-stock and out-of-stock thresholds for a product.
        Precedence:
          1. Active location-specific ReorderRule (active == True)
          2. Active product-wide ReorderRule (location_id == None, active == True)
          3. Product.reorder_level
        Compares AVAILABLE stock (quantity - reserved_quantity) against the threshold.
        """
        product = cls._get_active_product(db, product_id)

        # 1. Determine threshold from active ReorderRule or Product default
        reorder_rule = None
        if location_id is not None:
            reorder_rule = (
                db.query(ReorderRule)
                .filter(
                    ReorderRule.product_id == product_id,
                    ReorderRule.location_id == location_id,
                    ReorderRule.active.is_(True),
                )
                .first()
            )

        if not reorder_rule:
            reorder_rule = (
                db.query(ReorderRule)
                .filter(
                    ReorderRule.product_id == product_id,
                    ReorderRule.location_id.is_(None),
                    ReorderRule.active.is_(True),
                )
                .first()
            )

        if reorder_rule:
            threshold = reorder_rule.minimum_quantity
            reorder_qty = reorder_rule.reorder_quantity
        else:
            threshold = product.reorder_level
            reorder_qty = product.reorder_quantity

        # 2. Calculate stock levels based on AVAILABLE stock
        if location_id is not None:
            total_qty = cls.get_stock(db, product_id, location_id)
            avail_qty = cls.get_available_stock(db, product_id, location_id)
        else:
            inv_rows = (
                db.query(Inventory).filter(Inventory.product_id == product_id).all()
            )
            total_qty = sum((row.quantity for row in inv_rows), Decimal("0.0000"))
            avail_qty = sum(
                (row.quantity - row.reserved_quantity for row in inv_rows),
                Decimal("0.0000"),
            )

        is_low_stock = avail_qty <= threshold
        is_out_of_stock = avail_qty <= Decimal("0.0000")

        return {
            "product_id": product_id,
            "product_sku": product.sku,
            "product_name": product.name,
            "location_id": location_id,
            "total_quantity": total_qty,
            "available_quantity": avail_qty,
            "reorder_level": threshold,
            "reorder_quantity": reorder_qty,
            "is_low_stock": is_low_stock,
            "is_out_of_stock": is_out_of_stock,
        }
