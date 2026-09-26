from decimal import Decimal
import pytest
from app.models import (
    Adjustment,
    AdjustmentStatus,
    Inventory,
    LedgerTransactionType,
    Location,
    Product,
    StockLedger,
    User,
    Warehouse,
)


@pytest.fixture
def manager_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Manager Adj",
            "email": "mgr_adj@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "mgr_adj@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Staff Adj",
            "email": "staff_adj@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "staff_adj@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def setup_adj_data(db_session):
    wh = Warehouse(name="Main Warehouse", code="WH-ADJ-1", is_active=True)
    db_session.add(wh)
    db_session.commit()

    loc = Location(warehouse_id=wh.id, name="Storage A", code="LOC-ADJ-1", is_active=True)
    db_session.add(loc)
    db_session.commit()

    p1 = Product(name="Widget A", sku="WIDGET-001", unit_of_measure="pcs", is_active=True)
    p2 = Product(name="Gadget B", sku="GADGET-001", unit_of_measure="pcs", is_active=True)
    db_session.add_all([p1, p2])
    db_session.commit()

    # Initial inventory: p1 at loc has 80 units
    inv1 = Inventory(
        product_id=p1.id,
        location_id=loc.id,
        quantity=Decimal("80.0000"),
        reserved_quantity=Decimal("0.0000"),
    )
    db_session.add(inv1)
    db_session.commit()

    return {
        "wh_id": wh.id,
        "loc_id": loc.id,
        "p1_id": p1.id,
        "p2_id": p2.id,
    }


def test_auth_required(client):
    resp = client.get("/api/adjustments")
    assert resp.status_code == 401

    resp = client.post(
        "/api/adjustments",
        json={"product_id": 1, "location_id": 1, "counted_quantity": 10},
    )
    assert resp.status_code == 401


def test_manager_staff_access_and_creation(client, manager_token, staff_token, setup_adj_data):
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    # Manager creates adjustment
    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 77},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert Decimal(str(data["counted_quantity"])) == Decimal("77")
    assert Decimal(str(data["system_quantity"])) == Decimal("80")
    assert Decimal(str(data["difference"])) == Decimal("-3")

    # Staff creates adjustment
    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 85},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 201


def test_creation_no_draft_mutation_or_ledger(client, manager_token, setup_adj_data, db_session):
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 77},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201

    # Verify inventory in DB is untouched
    inv = (
        db_session.query(Inventory)
        .filter(Inventory.product_id == p1_id, Inventory.location_id == loc_id)
        .first()
    )
    assert inv.quantity == Decimal("80.0000")

    # Verify no ADJUSTMENT ledger entry created
    ledgers = (
        db_session.query(StockLedger)
        .filter(StockLedger.transaction_type == LedgerTransactionType.ADJUSTMENT)
        .all()
    )
    assert len(ledgers) == 0


def test_decimal_quantities_and_negative_rejected(client, manager_token, setup_adj_data):
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    # Decimal counted_quantity
    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": "77.5000"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    assert Decimal(str(resp.json()["counted_quantity"])) == Decimal("77.5")

    # Negative counted_quantity rejected
    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": -5},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 422 or resp.status_code == 400


def test_inactive_product_location_warehouse_rejected(client, manager_token, setup_adj_data, db_session):
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    # Inactive product
    p_inactive = Product(name="Inactive Prod", sku="INACT-001", unit_of_measure="pcs", is_active=False)
    db_session.add(p_inactive)
    db_session.commit()

    resp = client.post(
        "/api/adjustments",
        json={"product_id": p_inactive.id, "location_id": loc_id, "counted_quantity": 10},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()

    # Inactive location
    wh2 = Warehouse(name="WH2", code="WH2-ADJ", is_active=True)
    db_session.add(wh2)
    db_session.commit()
    loc_inactive = Location(warehouse_id=wh2.id, name="Loc Inactive", code="LOC-INACT", is_active=False)
    db_session.add(loc_inactive)
    db_session.commit()

    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_inactive.id, "counted_quantity": 10},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()

    # Location in inactive warehouse
    wh_inactive = Warehouse(name="WH Inactive", code="WH-INACT", is_active=False)
    db_session.add(wh_inactive)
    db_session.commit()
    loc_in_inact_wh = Location(warehouse_id=wh_inactive.id, name="Loc Wh Inact", code="LOC-WH-INACT", is_active=True)
    db_session.add(loc_in_inact_wh)
    db_session.commit()

    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_in_inact_wh.id, "counted_quantity": 10},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()


def test_official_mandatory_example_80_to_77(client, manager_token, setup_adj_data, db_session):
    """
    Mandatory Official Example:
    system = 80
    counted = 77
    difference = -3
    final stock = 77
    """
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    # 1. Create adjustment draft
    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 77, "reason": "Physical Count Audit"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    adj_id = resp.json()["id"]

    # 2. Validate adjustment
    v_resp = client.post(
        f"/api/adjustments/{adj_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert v_data["status"] == "DONE"
    assert Decimal(str(v_data["system_quantity"])) == Decimal("80")
    assert Decimal(str(v_data["counted_quantity"])) == Decimal("77")
    assert Decimal(str(v_data["difference"])) == Decimal("-3")

    # 3. Verify stock in DB
    inv = (
        db_session.query(Inventory)
        .filter(Inventory.product_id == p1_id, Inventory.location_id == loc_id)
        .first()
    )
    assert inv.quantity == Decimal("77.0000")

    # 4. Verify stock ledger entry
    ledger = (
        db_session.query(StockLedger)
        .filter(
            StockLedger.transaction_type == LedgerTransactionType.ADJUSTMENT,
            StockLedger.reference_id == str(adj_id),
        )
        .first()
    )
    assert ledger is not None
    assert ledger.quantity_before == Decimal("80.0000")
    assert ledger.quantity_change == Decimal("-3.0000")
    assert ledger.quantity_after == Decimal("77.0000")


def test_positive_adjustment(client, manager_token, setup_adj_data, db_session):
    """
    77 -> 90:
    ledger quantity_change = +13
    """
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    # Set stock to 77 first
    inv = (
        db_session.query(Inventory)
        .filter(Inventory.product_id == p1_id, Inventory.location_id == loc_id)
        .first()
    )
    inv.quantity = Decimal("77.0000")
    db_session.commit()

    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 90},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id = resp.json()["id"]

    v_resp = client.post(
        f"/api/adjustments/{adj_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert Decimal(str(v_data["system_quantity"])) == Decimal("77")
    assert Decimal(str(v_data["counted_quantity"])) == Decimal("90")
    assert Decimal(str(v_data["difference"])) == Decimal("13")

    inv = (
        db_session.query(Inventory)
        .filter(Inventory.product_id == p1_id, Inventory.location_id == loc_id)
        .first()
    )
    assert inv.quantity == Decimal("90.0000")

    ledger = (
        db_session.query(StockLedger)
        .filter(
            StockLedger.transaction_type == LedgerTransactionType.ADJUSTMENT,
            StockLedger.reference_id == str(adj_id),
        )
        .first()
    )
    assert ledger.quantity_before == Decimal("77.0000")
    assert ledger.quantity_change == Decimal("13.0000")
    assert ledger.quantity_after == Decimal("90.0000")


def test_zero_difference_adjustment(client, manager_token, setup_adj_data, db_session):
    """
    80 -> 80:
    follow existing InventoryService semantics exactly (creates zero-change ledger).
    """
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 80},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id = resp.json()["id"]

    v_resp = client.post(
        f"/api/adjustments/{adj_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert Decimal(str(v_data["difference"])) == Decimal("0")

    ledger = (
        db_session.query(StockLedger)
        .filter(
            StockLedger.transaction_type == LedgerTransactionType.ADJUSTMENT,
            StockLedger.reference_id == str(adj_id),
        )
        .first()
    )
    assert ledger is not None
    assert ledger.quantity_before == Decimal("80.0000")
    assert ledger.quantity_change == Decimal("0.0000")
    assert ledger.quantity_after == Decimal("80.0000")


def test_below_reservation_rejection(client, manager_token, setup_adj_data, db_session):
    """
    Reservation safety:
    system=100
    reserved=30
    counted=20
    must fail and stock remain unchanged.
    """
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    inv = (
        db_session.query(Inventory)
        .filter(Inventory.product_id == p1_id, Inventory.location_id == loc_id)
        .first()
    )
    inv.quantity = Decimal("100.0000")
    inv.reserved_quantity = Decimal("30.0000")
    db_session.commit()

    # Create draft adjustment with counted=20
    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 20},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    adj_id = resp.json()["id"]

    # Validate adjustment -> expect failure because counted (20) < reserved (30)
    v_resp = client.post(
        f"/api/adjustments/{adj_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v_resp.status_code == 400
    assert "reserved" in v_resp.json()["detail"].lower()

    # Stock remains untouched (100)
    db_session.refresh(inv)
    assert inv.quantity == Decimal("100.0000")

    # Status remains DRAFT
    adj = db_session.query(Adjustment).filter(Adjustment.id == adj_id).first()
    assert adj.status == AdjustmentStatus.DRAFT


def test_stale_stock_validation_semantics(client, manager_token, setup_adj_data, db_session):
    """
    IMPORTANT STALE-STOCK RULE:
    Draft sees 80 and count entered 77 (diff = -3).
    If system stock becomes 90 before validation, final adjustment must follow centralized
    adjust_stock semantics for counted quantity 77, resulting difference -13 and final 77.
    """
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    # 1. Create draft when system stock is 80
    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 77},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id = resp.json()["id"]

    # 2. System stock changes to 90 before validation
    inv = (
        db_session.query(Inventory)
        .filter(Inventory.product_id == p1_id, Inventory.location_id == loc_id)
        .first()
    )
    inv.quantity = Decimal("90.0000")
    db_session.commit()

    # 3. Validate adjustment
    v_resp = client.post(
        f"/api/adjustments/{adj_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v_resp.status_code == 200
    v_data = v_resp.json()

    # System quantity recorded at validation must be 90, difference -13, final counted 77
    assert Decimal(str(v_data["system_quantity"])) == Decimal("90")
    assert Decimal(str(v_data["counted_quantity"])) == Decimal("77")
    assert Decimal(str(v_data["difference"])) == Decimal("-13")

    # Inventory quantity in DB is 77
    db_session.refresh(inv)
    assert inv.quantity == Decimal("77.0000")

    # Ledger entry records -13 change
    ledger = (
        db_session.query(StockLedger)
        .filter(
            StockLedger.transaction_type == LedgerTransactionType.ADJUSTMENT,
            StockLedger.reference_id == str(adj_id),
        )
        .first()
    )
    assert ledger.quantity_before == Decimal("90.0000")
    assert ledger.quantity_change == Decimal("-13.0000")
    assert ledger.quantity_after == Decimal("77.0000")


def test_double_validation_prevention(client, manager_token, setup_adj_data, db_session):
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 75},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id = resp.json()["id"]

    # First validation succeeds
    v1 = client.post(
        f"/api/adjustments/{adj_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v1.status_code == 200

    # Second validation fails
    v2 = client.post(
        f"/api/adjustments/{adj_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v2.status_code == 400
    assert "already" in v2.json()["detail"].lower()

    # Stock adjusted only once (80 -> 75)
    inv = (
        db_session.query(Inventory)
        .filter(Inventory.product_id == p1_id, Inventory.location_id == loc_id)
        .first()
    )
    assert inv.quantity == Decimal("75.0000")

    # Exactly one ledger entry
    ledgers = (
        db_session.query(StockLedger)
        .filter(
            StockLedger.transaction_type == LedgerTransactionType.ADJUSTMENT,
            StockLedger.reference_id == str(adj_id),
        )
        .all()
    )
    assert len(ledgers) == 1


def test_cancellation_and_terminal_immutability(client, manager_token, setup_adj_data):
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    # 1. Create draft and cancel
    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 50},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id = resp.json()["id"]

    c_resp = client.post(
        f"/api/adjustments/{adj_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert c_resp.status_code == 200
    assert c_resp.json()["status"] == "CANCELED"

    # Canceled cannot validate
    v_resp = client.post(
        f"/api/adjustments/{adj_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v_resp.status_code == 400

    # Canceled cannot update
    p_resp = client.patch(
        f"/api/adjustments/{adj_id}",
        json={"counted_quantity": 60},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert p_resp.status_code == 400

    # 2. DONE immutable test
    resp2 = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 50},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id2 = resp2.json()["id"]

    client.post(
        f"/api/adjustments/{adj_id2}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    # DONE cannot cancel
    c_resp2 = client.post(
        f"/api/adjustments/{adj_id2}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert c_resp2.status_code == 400

    # DONE cannot update
    p_resp2 = client.patch(
        f"/api/adjustments/{adj_id2}",
        json={"counted_quantity": 60},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert p_resp2.status_code == 400

    # 3. Direct PATCH cannot set DONE or CANCELED
    resp3 = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 50},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id3 = resp3.json()["id"]

    patch_done = client.patch(
        f"/api/adjustments/{adj_id3}",
        json={"status": "DONE"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert patch_done.status_code == 400 or patch_done.status_code == 422

    patch_canceled = client.patch(
        f"/api/adjustments/{adj_id3}",
        json={"status": "CANCELED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert patch_canceled.status_code == 400 or patch_canceled.status_code == 422


def test_validation_time_inactive_resource_recheck(client, manager_token, setup_adj_data, db_session):
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 70},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id = resp.json()["id"]

    # Product becomes inactive before validation
    p1 = db_session.query(Product).filter(Product.id == p1_id).first()
    p1.is_active = False
    db_session.commit()

    v_resp = client.post(
        f"/api/adjustments/{adj_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v_resp.status_code == 400
    assert "inactive" in v_resp.json()["detail"].lower()

    # Stock remains untouched
    inv = (
        db_session.query(Inventory)
        .filter(Inventory.product_id == p1_id, Inventory.location_id == loc_id)
        .first()
    )
    assert inv.quantity == Decimal("80.0000")


def test_list_and_get_adjustments(client, manager_token, setup_adj_data):
    loc_id = setup_adj_data["loc_id"]
    p1_id = setup_adj_data["p1_id"]

    resp = client.post(
        "/api/adjustments",
        json={"product_id": p1_id, "location_id": loc_id, "counted_quantity": 77, "reason": "Audit search test"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id = resp.json()["id"]

    # GET by ID
    g_resp = client.get(
        f"/api/adjustments/{adj_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert g_resp.status_code == 200
    assert g_resp.json()["id"] == adj_id

    # GET list with filters
    l_resp = client.get(
        f"/api/adjustments?product_id={p1_id}&status=DRAFT&search=Audit",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert l_resp.status_code == 200
    assert len(l_resp.json()) >= 1
