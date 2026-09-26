from decimal import Decimal
import pytest
from app.models import Category, Inventory, Location, Product, ReorderRule, StockLedger, Warehouse
from app.models.enums import LedgerTransactionType
from app.services.inventory_service import (
    InventoryError,
    InventoryService,
    InsufficientStockError,
    InvalidAdjustmentError,
    InvalidQuantityError,
    InvalidTransactionTypeError,
    InvalidTransferError,
    LocationNotFoundError,
    ProductNotFoundError,
)


@pytest.fixture
def setup_inventory_fixtures(db_session):
    """Fixture providing standard active Category, Product, Warehouse, and Locations."""
    cat = Category(name="Electronics")
    db_session.add(cat)
    db_session.commit()

    product = Product(
        name="Smartphone",
        sku="SKU-PHONE-01",
        category_id=cat.id,
        reorder_level=Decimal("15.0000"),
        reorder_quantity=Decimal("50.0000"),
    )
    warehouse = Warehouse(name="Main WH", code="WH-MAIN")
    db_session.add_all([product, warehouse])
    db_session.commit()

    loc_src = Location(warehouse_id=warehouse.id, name="Aisle 1", code="LOC-A1")
    loc_dst = Location(warehouse_id=warehouse.id, name="Aisle 2", code="LOC-A2")
    db_session.add_all([loc_src, loc_dst])
    db_session.commit()

    return {
        "cat": cat,
        "product": product,
        "warehouse": warehouse,
        "loc_src": loc_src,
        "loc_dst": loc_dst,
    }


def test_01_get_stock_returns_zero_when_absent(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    stock = InventoryService.get_stock(db_session, p_id, l_id)
    assert stock == Decimal("0.0000")


def test_02_get_available_stock_returns_correct_value(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    inv = Inventory(
        product_id=p_id,
        location_id=l_id,
        quantity=Decimal("100.0000"),
        reserved_quantity=Decimal("30.0000"),
    )
    db_session.add(inv)
    db_session.commit()

    avail = InventoryService.get_available_stock(db_session, p_id, l_id)
    assert avail == Decimal("70.0000")


def test_03_increase_creates_inventory_row_if_absent(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    inv = InventoryService.increase_stock(
        db_session,
        product_id=p_id,
        location_id=l_id,
        quantity=Decimal("100.0000"),
        reference_id="REC-001",
    )
    assert inv.id is not None
    assert inv.quantity == Decimal("100.0000")
    assert inv.reserved_quantity == Decimal("0.0000")


def test_04_increase_updates_existing_inventory(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("50.0000"))
    inv2 = InventoryService.increase_stock(db_session, p_id, l_id, Decimal("30.0000"))
    assert inv2.quantity == Decimal("80.0000")


def test_05_increase_ledger_generated(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(
        db_session, p_id, l_id, Decimal("100.0000"), reference_id="REC-100"
    )

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == "REC-100")
        .first()
    )
    assert ledger is not None
    assert ledger.transaction_type == LedgerTransactionType.RECEIPT
    assert ledger.product_id == p_id
    assert ledger.destination_location_id == l_id
    assert ledger.quantity_before == Decimal("0.0000")
    assert ledger.quantity_change == Decimal("100.0000")
    assert ledger.quantity_after == Decimal("100.0000")


def test_06_decrease_stock_succeeds(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("100.0000"))
    inv_after = InventoryService.decrease_stock(
        db_session, p_id, l_id, Decimal("20.0000"), reference_id="DEL-001"
    )
    assert inv_after.quantity == Decimal("80.0000")


def test_07_decrease_ledger_generated_with_negative_change(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("100.0000"))
    InventoryService.decrease_stock(
        db_session, p_id, l_id, Decimal("20.0000"), reference_id="DEL-002"
    )

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == "DEL-002")
        .first()
    )
    assert ledger is not None
    assert ledger.transaction_type == LedgerTransactionType.DELIVERY
    assert ledger.source_location_id == l_id
    assert ledger.quantity_before == Decimal("100.0000")
    assert ledger.quantity_change == Decimal("-20.0000")
    assert ledger.quantity_after == Decimal("80.0000")


def test_08_decrease_rejects_insufficient_physical_stock(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    with pytest.raises(InsufficientStockError):
        InventoryService.decrease_stock(db_session, p_id, l_id, Decimal("10.0000"))


def test_09_decrease_rejects_insufficient_available_stock_due_to_reservation(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    inv = InventoryService.increase_stock(db_session, p_id, l_id, Decimal("100.0000"))
    inv.reserved_quantity = Decimal("30.0000")
    db_session.commit()

    with pytest.raises(InsufficientStockError):
        InventoryService.decrease_stock(db_session, p_id, l_id, Decimal("80.0000"))


def test_10_rejected_decrease_leaves_stock_unchanged(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("50.0000"))

    with pytest.raises(InsufficientStockError):
        InventoryService.decrease_stock(db_session, p_id, l_id, Decimal("100.0000"))

    stock = InventoryService.get_stock(db_session, p_id, l_id)
    assert stock == Decimal("50.0000")


def test_11_rejected_decrease_creates_no_ledger(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    with pytest.raises(InsufficientStockError):
        InventoryService.decrease_stock(
            db_session, p_id, l_id, Decimal("10.0000"), reference_id="FAIL-DEL"
        )

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == "FAIL-DEL")
        .first()
    )
    assert ledger is None


def test_12_zero_quantity_rejected(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    with pytest.raises(InvalidQuantityError):
        InventoryService.increase_stock(db_session, p_id, l_id, Decimal("0.0000"))


def test_13_negative_quantity_rejected(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    with pytest.raises(InvalidQuantityError):
        InventoryService.increase_stock(db_session, p_id, l_id, Decimal("-15.0000"))


def test_14_transfer_moves_stock_source_to_destination(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id
    dst_id = setup_inventory_fixtures["loc_dst"].id

    InventoryService.increase_stock(db_session, p_id, src_id, Decimal("100.0000"))
    src_inv, dst_inv = InventoryService.transfer_stock(
        db_session, p_id, src_id, dst_id, Decimal("40.0000"), reference_id="TR-001"
    )

    assert src_inv.quantity == Decimal("60.0000")
    assert dst_inv.quantity == Decimal("40.0000")


def test_15_transfer_creates_destination_row_if_absent(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id
    dst_id = setup_inventory_fixtures["loc_dst"].id

    InventoryService.increase_stock(db_session, p_id, src_id, Decimal("50.0000"))

    dst_db_before = (
        db_session.query(Inventory)
        .filter(Inventory.product_id == p_id, Inventory.location_id == dst_id)
        .first()
    )
    assert dst_db_before is None

    _, dst_inv = InventoryService.transfer_stock(
        db_session, p_id, src_id, dst_id, Decimal("20.0000")
    )
    assert dst_inv.id is not None
    assert dst_inv.quantity == Decimal("20.0000")


def test_16_transfer_preserves_company_total(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id
    dst_id = setup_inventory_fixtures["loc_dst"].id

    InventoryService.increase_stock(db_session, p_id, src_id, Decimal("100.0000"))
    InventoryService.increase_stock(db_session, p_id, dst_id, Decimal("50.0000"))

    total_before = InventoryService.get_stock(db_session, p_id, src_id) + InventoryService.get_stock(db_session, p_id, dst_id)
    assert total_before == Decimal("150.0000")

    InventoryService.transfer_stock(db_session, p_id, src_id, dst_id, Decimal("35.0000"))

    total_after = InventoryService.get_stock(db_session, p_id, src_id) + InventoryService.get_stock(db_session, p_id, dst_id)
    assert total_after == Decimal("150.0000")


def test_17_transfer_source_equals_destination_rejected(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id

    with pytest.raises(InvalidTransferError):
        InventoryService.transfer_stock(db_session, p_id, src_id, src_id, Decimal("10.0000"))


def test_18_insufficient_transfer_rejected(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id
    dst_id = setup_inventory_fixtures["loc_dst"].id

    InventoryService.increase_stock(db_session, p_id, src_id, Decimal("20.0000"))

    with pytest.raises(InsufficientStockError):
        InventoryService.transfer_stock(db_session, p_id, src_id, dst_id, Decimal("50.0000"))


def test_19_failed_transfer_does_not_partially_change_destination(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id
    dst_id = setup_inventory_fixtures["loc_dst"].id

    InventoryService.increase_stock(db_session, p_id, src_id, Decimal("10.0000"))
    InventoryService.increase_stock(db_session, p_id, dst_id, Decimal("5.0000"))

    with pytest.raises(InsufficientStockError):
        InventoryService.transfer_stock(db_session, p_id, src_id, dst_id, Decimal("50.0000"))

    assert InventoryService.get_stock(db_session, p_id, src_id) == Decimal("10.0000")
    assert InventoryService.get_stock(db_session, p_id, dst_id) == Decimal("5.0000")


def test_20_transfer_ledger_generated_correctly(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id
    dst_id = setup_inventory_fixtures["loc_dst"].id

    InventoryService.increase_stock(db_session, p_id, src_id, Decimal("100.0000"))
    InventoryService.transfer_stock(
        db_session, p_id, src_id, dst_id, Decimal("30.0000"), reference_id="TRF-99"
    )

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == "TRF-99")
        .first()
    )
    assert ledger is not None
    assert ledger.transaction_type == LedgerTransactionType.TRANSFER
    assert ledger.source_location_id == src_id
    assert ledger.destination_location_id == dst_id
    assert ledger.quantity_before == Decimal("100.0000")
    assert ledger.quantity_change == Decimal("30.0000")
    assert ledger.quantity_after == Decimal("70.0000")


def test_21_negative_adjustment_works_system_80_counted_77(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("80.0000"))
    inv_adj = InventoryService.adjust_stock(
        db_session, p_id, l_id, counted_quantity=Decimal("77.0000"), reference_id="ADJ-001"
    )
    assert inv_adj.quantity == Decimal("77.0000")

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == "ADJ-001")
        .first()
    )
    assert ledger.transaction_type == LedgerTransactionType.ADJUSTMENT
    assert ledger.quantity_before == Decimal("80.0000")
    assert ledger.quantity_change == Decimal("-3.0000")
    assert ledger.quantity_after == Decimal("77.0000")


def test_22_positive_adjustment_works(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("50.0000"))
    inv_adj = InventoryService.adjust_stock(
        db_session, p_id, l_id, counted_quantity=Decimal("60.0000"), reference_id="ADJ-002"
    )
    assert inv_adj.quantity == Decimal("60.0000")

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == "ADJ-002")
        .first()
    )
    assert ledger.quantity_change == Decimal("10.0000")


def test_23_adjustment_to_same_quantity_creates_zero_change_ledger(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("50.0000"))
    InventoryService.adjust_stock(
        db_session, p_id, l_id, counted_quantity=Decimal("50.0000"), reference_id="ADJ-SAME"
    )

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == "ADJ-SAME")
        .first()
    )
    assert ledger.quantity_change == Decimal("0.0000")


def test_24_negative_counted_quantity_rejected(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    with pytest.raises(InvalidQuantityError):
        InventoryService.adjust_stock(db_session, p_id, l_id, counted_quantity=Decimal("-5.0000"))


def test_25_adjustment_below_reserved_quantity_rejected(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    inv = InventoryService.increase_stock(db_session, p_id, l_id, Decimal("100.0000"))
    inv.reserved_quantity = Decimal("40.0000")
    db_session.commit()

    with pytest.raises(InvalidAdjustmentError):
        InventoryService.adjust_stock(db_session, p_id, l_id, counted_quantity=Decimal("30.0000"))


def test_26_initial_stock_generates_initial_stock_ledger(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    inv = InventoryService.set_initial_stock(
        db_session, p_id, l_id, Decimal("200.0000"), reference_id="INIT-001"
    )
    assert inv.quantity == Decimal("200.0000")

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == "INIT-001")
        .first()
    )
    assert ledger.transaction_type == LedgerTransactionType.INITIAL_STOCK
    assert ledger.quantity_change == Decimal("200.0000")


def test_27_decimal_precision_handling(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    inv = InventoryService.increase_stock(db_session, p_id, l_id, "12.34567")
    assert inv.quantity == Decimal("12.3457")


def test_28_location_or_product_validation(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    with pytest.raises(ProductNotFoundError):
        InventoryService.increase_stock(db_session, product_id=99999, location_id=l_id, quantity=10)

    with pytest.raises(LocationNotFoundError):
        InventoryService.increase_stock(db_session, product_id=p_id, location_id=99999, quantity=10)


def test_29_low_stock_and_out_of_stock_detection(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("10.0000"))

    res = InventoryService.check_low_stock(db_session, p_id, l_id)
    assert res["is_low_stock"] is True
    assert res["is_out_of_stock"] is False
    assert res["available_quantity"] == Decimal("10.0000")
    assert res["reorder_level"] == Decimal("15.0000")

    InventoryService.decrease_stock(db_session, p_id, l_id, Decimal("10.0000"))
    res_zero = InventoryService.check_low_stock(db_session, p_id, l_id)
    assert res_zero["is_low_stock"] is True
    assert res_zero["is_out_of_stock"] is True


def test_30_explicit_reorder_rule_overrides_product_reorder_level(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    rule = ReorderRule(
        product_id=p_id,
        location_id=l_id,
        minimum_quantity=Decimal("5.0000"),
        reorder_quantity=Decimal("20.0000"),
        active=True,
    )
    db_session.add(rule)
    db_session.commit()

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("10.0000"))
    res = InventoryService.check_low_stock(db_session, p_id, l_id)

    assert res["is_low_stock"] is False
    assert res["reorder_level"] == Decimal("5.0000")


def test_31_official_demo_arithmetic_sequence(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id
    dst_id = setup_inventory_fixtures["loc_dst"].id

    inv_src = InventoryService.increase_stock(db_session, p_id, src_id, Decimal("100.0000"))
    assert inv_src.quantity == Decimal("100.0000")

    src_inv, dst_inv = InventoryService.transfer_stock(db_session, p_id, src_id, dst_id, Decimal("30.0000"))
    assert src_inv.quantity == Decimal("70.0000")
    assert dst_inv.quantity == Decimal("30.0000")
    assert (src_inv.quantity + dst_inv.quantity) == Decimal("100.0000")

    src_after_del = InventoryService.decrease_stock(db_session, p_id, src_id, Decimal("20.0000"))
    assert src_after_del.quantity == Decimal("50.0000")

    loc_adj = setup_inventory_fixtures["loc_dst"]
    InventoryService.increase_stock(db_session, p_id, loc_adj.id, Decimal("50.0000"))
    assert InventoryService.get_stock(db_session, p_id, loc_adj.id) == Decimal("80.0000")

    adj_inv = InventoryService.adjust_stock(db_session, p_id, loc_adj.id, counted_quantity=Decimal("77.0000"))
    assert adj_inv.quantity == Decimal("77.0000")


def test_32_transaction_boundary_safety(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, src_id, Decimal("50.0000"))
    db_session.rollback()

    assert InventoryService.get_stock(db_session, p_id, src_id) == Decimal("0.0000")


# ============================================================================
# AUDIT & INVARIANT TESTS
# ============================================================================

def test_33_invalid_transaction_type_rejected_in_increase(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    with pytest.raises(InvalidTransactionTypeError):
        InventoryService.increase_stock(
            db_session, p_id, l_id, Decimal("10.0000"), transaction_type=LedgerTransactionType.DELIVERY
        )

    assert InventoryService.get_stock(db_session, p_id, l_id) == Decimal("0.0000")
    ledger = db_session.query(StockLedger).filter(StockLedger.product_id == p_id).first()
    assert ledger is None


def test_34_invalid_transaction_type_rejected_in_decrease(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("50.0000"))

    with pytest.raises(InvalidTransactionTypeError):
        InventoryService.decrease_stock(
            db_session, p_id, l_id, Decimal("10.0000"), transaction_type=LedgerTransactionType.RECEIPT
        )

    assert InventoryService.get_stock(db_session, p_id, l_id) == Decimal("50.0000")


def test_35_inactive_product_or_location_rejected(db_session, setup_inventory_fixtures):
    product = setup_inventory_fixtures["product"]
    loc_src = setup_inventory_fixtures["loc_src"]
    loc_dst = setup_inventory_fixtures["loc_dst"]

    # Deactivate product
    product.is_active = False
    db_session.commit()

    with pytest.raises(ProductNotFoundError):
        InventoryService.increase_stock(db_session, product.id, loc_src.id, Decimal("10.0000"))

    # Re-activate product, deactivate source location
    product.is_active = True
    loc_src.is_active = False
    db_session.commit()

    with pytest.raises(LocationNotFoundError):
        InventoryService.increase_stock(db_session, product.id, loc_src.id, Decimal("10.0000"))

    # Transfer with inactive destination location
    loc_src.is_active = True
    loc_dst.is_active = False
    db_session.commit()

    InventoryService.increase_stock(db_session, product.id, loc_src.id, Decimal("50.0000"))
    with pytest.raises(LocationNotFoundError):
        InventoryService.transfer_stock(db_session, product.id, loc_src.id, loc_dst.id, Decimal("10.0000"))


def test_36_reserved_quantity_invariants(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id
    dst_id = setup_inventory_fixtures["loc_dst"].id

    inv = InventoryService.increase_stock(db_session, p_id, src_id, Decimal("100.0000"))
    inv.reserved_quantity = Decimal("60.0000")
    db_session.commit()

    # Attempt transfer of 50 -> available stock is 40 -> rejected
    with pytest.raises(InsufficientStockError):
        InventoryService.transfer_stock(db_session, p_id, src_id, dst_id, Decimal("50.0000"))

    # Verify invariants hold
    inv_db = db_session.query(Inventory).filter(Inventory.id == inv.id).first()
    assert inv_db.reserved_quantity >= Decimal("0.0000")
    assert inv_db.quantity >= inv_db.reserved_quantity


def test_37_transfer_caller_rollback_atomicity(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id
    dst_id = setup_inventory_fixtures["loc_dst"].id

    InventoryService.increase_stock(db_session, p_id, src_id, Decimal("100.0000"))
    db_session.commit()

    # Perform transfer in session but caller rolls back
    InventoryService.transfer_stock(db_session, p_id, src_id, dst_id, Decimal("40.0000"), reference_id="TRF-ROLLBACK")
    db_session.rollback()

    assert InventoryService.get_stock(db_session, p_id, src_id) == Decimal("100.0000")
    assert InventoryService.get_stock(db_session, p_id, dst_id) == Decimal("0.0000")

    ledger = db_session.query(StockLedger).filter(StockLedger.reference_id == "TRF-ROLLBACK").first()
    assert ledger is None


def test_38_ledger_commit_persists(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    src_id = setup_inventory_fixtures["loc_src"].id

    InventoryService.increase_stock(db_session, p_id, src_id, Decimal("50.0000"), reference_id="COMMITTED-REC")
    db_session.commit()

    ledger = db_session.query(StockLedger).filter(StockLedger.reference_id == "COMMITTED-REC").first()
    assert ledger is not None
    assert ledger.quantity_after == Decimal("50.0000")


def test_39_initial_stock_single_use_guard(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    # First initial stock call succeeds
    InventoryService.set_initial_stock(db_session, p_id, l_id, Decimal("100.0000"), reference_id="INIT-1")
    assert InventoryService.get_stock(db_session, p_id, l_id) == Decimal("100.0000")

    # Second initial stock call fails
    with pytest.raises(InvalidAdjustmentError):
        InventoryService.set_initial_stock(db_session, p_id, l_id, Decimal("50.0000"), reference_id="INIT-2")


def test_40_inactive_reorder_rule_ignored(db_session, setup_inventory_fixtures):
    p_id = setup_inventory_fixtures["product"].id
    l_id = setup_inventory_fixtures["loc_src"].id

    # Product reorder_level = 15. Create INACTIVE rule with min = 5
    rule = ReorderRule(
        product_id=p_id,
        location_id=l_id,
        minimum_quantity=Decimal("5.0000"),
        reorder_quantity=Decimal("20.0000"),
        active=False,
    )
    db_session.add(rule)
    db_session.commit()

    InventoryService.increase_stock(db_session, p_id, l_id, Decimal("10.0000"))
    res = InventoryService.check_low_stock(db_session, p_id, l_id)

    # Inactive rule must be ignored -> falls back to product reorder_level = 15.0000
    # Available = 10 <= 15 -> is_low_stock should be True
    assert res["is_low_stock"] is True
    assert res["reorder_level"] == Decimal("15.0000")
