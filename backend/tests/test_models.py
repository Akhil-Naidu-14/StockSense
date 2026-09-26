from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Adjustment,
    AdjustmentStatus,
    Category,
    Delivery,
    DeliveryItem,
    DeliveryStatus,
    Inventory,
    LedgerTransactionType,
    Location,
    PasswordResetOTP,
    Product,
    Receipt,
    ReceiptItem,
    ReceiptStatus,
    ReorderRule,
    StockLedger,
    Transfer,
    TransferItem,
    TransferStatus,
    User,
    UserRole,
    Warehouse,
)


def test_user_and_otp_creation(db_session):
    user = User(
        name="John Doe",
        email="john@example.com",
        password_hash="hashed_secret",
        role=UserRole.INVENTORY_MANAGER,
        phone="+1234567890",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.role == UserRole.INVENTORY_MANAGER
    assert user.is_active is True

    otp = PasswordResetOTP(
        user_id=user.id,
        otp="123456",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db_session.add(otp)
    db_session.commit()
    db_session.refresh(otp)

    assert otp.id is not None
    assert otp.user.email == "john@example.com"


def test_warehouse_location_category_product(db_session):
    user = User(
        name="Warehouse Mgr",
        email="mgr@example.com",
        password_hash="hashed_pwd",
        role=UserRole.INVENTORY_MANAGER,
    )
    category = Category(name="Electronics", description="Gadgets and gear")
    db_session.add_all([user, category])
    db_session.commit()

    warehouse = Warehouse(
        name="Central Hub",
        code="WH-01",
        address="123 Main St",
        manager_id=user.id,
    )
    db_session.add(warehouse)
    db_session.commit()

    location = Location(
        warehouse_id=warehouse.id,
        name="Rack A1",
        code="LOC-A1",
        location_type="internal",
    )
    product = Product(
        name="Laptop",
        sku="SKU-LAP-001",
        category_id=category.id,
        unit_of_measure="pcs",
        reorder_level=Decimal("5.0000"),
        reorder_quantity=Decimal("10.0000"),
    )
    db_session.add_all([location, product])
    db_session.commit()

    inventory = Inventory(
        product_id=product.id,
        location_id=location.id,
        quantity=Decimal("50.0000"),
        reserved_quantity=Decimal("5.0000"),
    )
    db_session.add(inventory)
    db_session.commit()

    assert inventory.id is not None
    assert inventory.product.name == "Laptop"
    assert inventory.location.warehouse.code == "WH-01"


def test_inventory_unique_constraint(db_session):
    category = Category(name="Test Cat")
    db_session.add(category)
    db_session.commit()

    warehouse = Warehouse(name="WH Test", code="WH-TST")
    db_session.add(warehouse)
    db_session.commit()

    location = Location(warehouse_id=warehouse.id, name="Loc 1", code="LOC-1")
    product = Product(name="Prod 1", sku="SKU-1", category_id=category.id)
    db_session.add_all([location, product])
    db_session.commit()

    inv1 = Inventory(product_id=product.id, location_id=location.id, quantity=Decimal("10"))
    db_session.add(inv1)
    db_session.commit()

    inv2 = Inventory(product_id=product.id, location_id=location.id, quantity=Decimal("20"))
    db_session.add(inv2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_transfer_multiple_location_foreign_keys(db_session):
    user = User(name="User 1", email="u1@example.com", password_hash="pass")
    wh = Warehouse(name="Main WH", code="WH-MAIN")
    db_session.add_all([user, wh])
    db_session.commit()

    loc1 = Location(warehouse_id=wh.id, name="Source Loc", code="LOC-SRC")
    loc2 = Location(warehouse_id=wh.id, name="Dest Loc", code="LOC-DST")
    product = Product(name="Item A", sku="SKU-A")
    db_session.add_all([loc1, loc2, product])
    db_session.commit()

    transfer = Transfer(
        transfer_number="TRF-001",
        source_location_id=loc1.id,
        destination_location_id=loc2.id,
        status=TransferStatus.DRAFT,
        created_by=user.id,
    )
    db_session.add(transfer)
    db_session.commit()

    item = TransferItem(transfer_id=transfer.id, product_id=product.id, quantity=Decimal("15.0000"))
    db_session.add(item)
    db_session.commit()

    assert transfer.source_location.code == "LOC-SRC"
    assert transfer.destination_location.code == "LOC-DST"
    assert len(transfer.items) == 1


def test_stock_ledger_foreign_keys(db_session):
    user = User(name="User 2", email="u2@example.com", password_hash="pass")
    wh = Warehouse(name="WH 2", code="WH-2")
    db_session.add_all([user, wh])
    db_session.commit()

    loc1 = Location(warehouse_id=wh.id, name="Loc A", code="LOC-A")
    loc2 = Location(warehouse_id=wh.id, name="Loc B", code="LOC-B")
    prod = Product(name="Item B", sku="SKU-B")
    db_session.add_all([loc1, loc2, prod])
    db_session.commit()

    ledger = StockLedger(
        transaction_type=LedgerTransactionType.TRANSFER,
        reference_id="TRF-001",
        product_id=prod.id,
        source_location_id=loc1.id,
        destination_location_id=loc2.id,
        quantity_before=Decimal("100.0000"),
        quantity_change=Decimal("-10.0000"),
        quantity_after=Decimal("90.0000"),
        reason="Stock Transfer",
        performed_by=user.id,
    )
    db_session.add(ledger)
    db_session.commit()

    assert ledger.source_location.code == "LOC-A"
    assert ledger.destination_location.code == "LOC-B"
    assert ledger.performer.email == "u2@example.com"


def test_delivery_status_enum(db_session):
    user = User(name="User 3", email="u3@example.com", password_hash="pass")
    wh = Warehouse(name="WH 3", code="WH-3")
    db_session.add_all([user, wh])
    db_session.commit()

    loc = Location(warehouse_id=wh.id, name="Shipping Loc", code="LOC-SHIP")
    db_session.add(loc)
    db_session.commit()

    for status in [
        DeliveryStatus.DRAFT,
        DeliveryStatus.WAITING,
        DeliveryStatus.READY,
        DeliveryStatus.PICKED,
        DeliveryStatus.PACKED,
        DeliveryStatus.DONE,
        DeliveryStatus.CANCELED,
    ]:
        delivery = Delivery(
            delivery_number=f"DEL-{status.value}",
            location_id=loc.id,
            status=status,
            created_by=user.id,
        )
        db_session.add(delivery)
    db_session.commit()
