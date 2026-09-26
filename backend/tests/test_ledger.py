from datetime import datetime, timezone
from decimal import Decimal
import pytest
from app.models import (
    Adjustment,
    AdjustmentStatus,
    Delivery,
    DeliveryItem,
    DeliveryStatus,
    Inventory,
    LedgerTransactionType,
    Location,
    Product,
    Receipt,
    ReceiptItem,
    ReceiptStatus,
    StockLedger,
    Transfer,
    TransferItem,
    TransferStatus,
    User,
    Warehouse,
)


@pytest.fixture
def manager_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Manager Ledger",
            "email": "mgr_ledger@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "mgr_ledger@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Staff Ledger",
            "email": "staff_ledger@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "staff_ledger@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def setup_ledger_data(db_session):
    wh1 = Warehouse(name="Warehouse A", code="WH-LED-1", is_active=True)
    wh2 = Warehouse(name="Warehouse B", code="WH-LED-2", is_active=True)
    db_session.add_all([wh1, wh2])
    db_session.commit()

    loc1 = Location(warehouse_id=wh1.id, name="Location 1", code="LOC-LED-1", is_active=True)
    loc2 = Location(warehouse_id=wh2.id, name="Location 2", code="LOC-LED-2", is_active=True)
    db_session.add_all([loc1, loc2])
    db_session.commit()

    prod = Product(name="Ledger Item", sku="LED-001", unit_of_measure="pcs", is_active=True)
    db_session.add(prod)
    db_session.commit()

    return {
        "wh1_id": wh1.id,
        "wh2_id": wh2.id,
        "loc1_id": loc1.id,
        "loc2_id": loc2.id,
        "prod_id": prod.id,
    }


def test_auth_required_for_ledger_and_move_history(client):
    assert client.get("/api/ledger").status_code == 401
    assert client.get("/api/ledger/1").status_code == 401
    assert client.get("/api/move-history").status_code == 401


def test_manager_staff_reads(client, manager_token, staff_token):
    # Manager read
    res1 = client.get("/api/ledger", headers={"Authorization": f"Bearer {manager_token}"})
    assert res1.status_code == 200

    # Staff read
    res2 = client.get("/api/ledger", headers={"Authorization": f"Bearer {staff_token}"})
    assert res2.status_code == 200

    # Move history read
    res3 = client.get("/api/move-history", headers={"Authorization": f"Bearer {staff_token}"})
    assert res3.status_code == 200


def test_official_end_to_end_ledger_workflow(client, manager_token, setup_ledger_data, db_session):
    """
    Official End-to-End Workflow Verification:
    1. Receipt: +100 at loc1 (loc1 stock = 100)
    2. Transfer: move 20 units from loc1 to loc2 (loc1 stock = 80, company total unchanged)
    3. Delivery: -20 units at loc2 (loc2 stock = 0, loc1 stock remains 80)
    4. Adjustment: physical count at loc1 (system = 80, counted = 77, difference = -3, final = 77)
    Verify ledger/move-history records.
    """
    loc1_id = setup_ledger_data["loc1_id"]
    loc2_id = setup_ledger_data["loc2_id"]
    prod_id = setup_ledger_data["prod_id"]

    # 1. RECEIPT: Receive 100 units at loc1
    r_resp = client.post(
        "/api/receipts",
        json={
            "supplier": "Acme Corp",
            "location_id": loc1_id,
            "items": [{"product_id": prod_id, "quantity": 100}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rcp_id = r_resp.json()["id"]
    client.patch(f"/api/receipts/{rcp_id}", json={"status": "RECEIVED"}, headers={"Authorization": f"Bearer {manager_token}"})
    client.post(f"/api/receipts/{rcp_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})

    # 2. TRANSFER: Transfer 20 units from loc1 to loc2 (loc1 becomes 80, loc2 becomes 20)
    trf_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": loc1_id,
            "destination_location_id": loc2_id,
            "items": [{"product_id": prod_id, "quantity": 20}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = trf_resp.json()["id"]
    client.patch(f"/api/transfers/{trf_id}", json={"status": "IN_TRANSIT"}, headers={"Authorization": f"Bearer {manager_token}"})
    client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})

    # 3. DELIVERY: Deliver 20 units from loc2 (loc2 stock becomes 0, loc1 stock remains 80)
    del_resp = client.post(
        "/api/deliveries",
        json={
            "customer_name": "Globex",
            "location_id": loc2_id,
            "items": [{"product_id": prod_id, "quantity": 20}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    del_id = del_resp.json()["id"]
    client.patch(f"/api/deliveries/{del_id}", json={"status": "READY"}, headers={"Authorization": f"Bearer {manager_token}"})
    client.patch(f"/api/deliveries/{del_id}", json={"status": "PICKED"}, headers={"Authorization": f"Bearer {manager_token}"})
    client.patch(f"/api/deliveries/{del_id}", json={"status": "PACKED"}, headers={"Authorization": f"Bearer {manager_token}"})
    client.post(f"/api/deliveries/{del_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})

    # 4. ADJUSTMENT: Count physical stock at loc1 (system stock = 80, counted = 77, diff = -3)
    adj_resp = client.post(
        "/api/adjustments",
        json={"product_id": prod_id, "location_id": loc1_id, "counted_quantity": 77, "reason": "Physical count audit"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    adj_id = adj_resp.json()["id"]
    v_adj = client.post(f"/api/adjustments/{adj_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert v_adj.status_code == 200
    adj_data = v_adj.json()

    assert Decimal(str(adj_data["system_quantity"])) == Decimal("80")
    assert Decimal(str(adj_data["counted_quantity"])) == Decimal("77")
    assert Decimal(str(adj_data["difference"])) == Decimal("-3")
    assert adj_data["status"] == "DONE"

    # Verify inventory in DB at loc1 is 77
    inv1 = db_session.query(Inventory).filter(Inventory.product_id == prod_id, Inventory.location_id == loc1_id).first()
    assert inv1.quantity == Decimal("77.0000")

    # Query GET /api/ledger
    ledger_resp = client.get("/api/ledger", headers={"Authorization": f"Bearer {manager_token}"})
    assert ledger_resp.status_code == 200
    entries = ledger_resp.json()
    assert len(entries) >= 4

    types_found = [e["transaction_type"] for e in entries]
    assert "RECEIPT" in types_found
    assert "TRANSFER" in types_found
    assert "DELIVERY" in types_found
    assert "ADJUSTMENT" in types_found

    # Query GET /api/move-history
    mh_resp = client.get("/api/move-history", headers={"Authorization": f"Bearer {manager_token}"})
    assert mh_resp.status_code == 200
    movements = mh_resp.json()
    assert len(movements) >= 4

    # Verify signs in Move History
    for m in movements:
        if m["type"] == "RECEIPT":
            assert Decimal(str(m["quantity"])) == Decimal("100")
        elif m["type"] == "DELIVERY":
            assert Decimal(str(m["quantity"])) == Decimal("-20")
        elif m["type"] == "ADJUSTMENT":
            assert Decimal(str(m["quantity"])) == Decimal("-3")
        elif m["type"] == "TRANSFER":
            assert Decimal(str(m["quantity"])) == Decimal("20")


def test_ledger_filtering_and_pagination(client, manager_token, setup_ledger_data, db_session):
    loc1_id = setup_ledger_data["loc1_id"]
    prod_id = setup_ledger_data["prod_id"]

    # Create dummy ledgers
    l1 = StockLedger(
        transaction_type=LedgerTransactionType.INITIAL_STOCK,
        product_id=prod_id,
        source_location_id=None,
        destination_location_id=loc1_id,
        quantity_before=Decimal("0.0000"),
        quantity_change=Decimal("50.0000"),
        quantity_after=Decimal("50.0000"),
        reference_id="INIT-001",
    )
    db_session.add(l1)
    db_session.commit()

    # Get detail
    detail_res = client.get(f"/api/ledger/{l1.id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert detail_res.status_code == 200
    assert detail_res.json()["reference_id"] == "INIT-001"

    # Missing detail 404
    missing_res = client.get("/api/ledger/999999", headers={"Authorization": f"Bearer {manager_token}"})
    assert missing_res.status_code == 404

    # Filter by transaction_type
    filter_res = client.get(
        f"/api/ledger?transaction_type=INITIAL_STOCK&product_id={prod_id}&location_id={loc1_id}&reference_id=INIT-001",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert filter_res.status_code == 200
    data = filter_res.json()
    assert len(data) >= 1

    # Pagination test
    page_res = client.get(
        "/api/ledger?limit=1&offset=0",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert page_res.status_code == 200
    assert len(page_res.json()) == 1
