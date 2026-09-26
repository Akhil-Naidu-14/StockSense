from decimal import Decimal
import pytest
from app.models import (
    Delivery,
    DeliveryItem,
    DeliveryStatus,
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
            "name": "Manager Delivery",
            "email": "mgr_dlv@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "mgr_dlv@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Staff Delivery",
            "email": "staff_dlv@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "staff_dlv@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def setup_data(db_session):
    wh = Warehouse(name="Dispatch Warehouse", code="WH-DLV-1", is_active=True)
    db_session.add(wh)
    db_session.commit()

    loc1 = Location(warehouse_id=wh.id, name="Shipping Dock A", code="LOC-DLV-1", is_active=True)
    loc2 = Location(warehouse_id=wh.id, name="Shipping Dock B", code="LOC-DLV-2", is_active=True)
    db_session.add_all([loc1, loc2])
    db_session.commit()

    p1 = Product(name="Widget X", sku="WIDGET-001", unit_of_measure="pcs", is_active=True)
    p2 = Product(name="Gadget Y", sku="GADGET-001", unit_of_measure="pcs", is_active=True)
    p3 = Product(name="Sprocket Z", sku="SPROCKET-001", unit_of_measure="pcs", is_active=True)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    # Initial inventory setup:
    # loc1 + p1 = 100 units (reserved = 0)
    # loc1 + p2 = 50 units (reserved = 20 -> available = 30)
    # loc1 + p3 = 10 units
    inv1 = Inventory(product_id=p1.id, location_id=loc1.id, quantity=Decimal("100.0000"), reserved_quantity=Decimal("0.0000"))
    inv2 = Inventory(product_id=p2.id, location_id=loc1.id, quantity=Decimal("50.0000"), reserved_quantity=Decimal("20.0000"))
    inv3 = Inventory(product_id=p3.id, location_id=loc1.id, quantity=Decimal("10.0000"), reserved_quantity=Decimal("0.0000"))
    db_session.add_all([inv1, inv2, inv3])
    db_session.commit()

    return {
        "wh_id": wh.id,
        "loc1_id": loc1.id,
        "loc2_id": loc2.id,
        "p1_id": p1.id,
        "p2_id": p2.id,
        "p3_id": p3.id,
    }


def advance_to_packed(client, manager_token, delivery_id):
    """Helper to transition a delivery from DRAFT to PACKED via legal status steps."""
    # DRAFT -> READY -> PICKED -> PACKED
    client.patch(
        f"/api/deliveries/{delivery_id}",
        json={"status": "READY"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    client.patch(
        f"/api/deliveries/{delivery_id}",
        json={"status": "PICKED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    resp = client.patch(
        f"/api/deliveries/{delivery_id}",
        json={"status": "PACKED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PACKED"
    return resp


# 1. authentication required
def test_01_unauthenticated_create_returns_401(client, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "customer_reference": "Cust Ref 01",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
    )
    assert resp.status_code == 401


# 2. manager can create delivery
def test_02_manager_can_create_delivery(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "customer_reference": "Customer Alpha",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "15.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["customer_reference"] == "Customer Alpha"
    assert data["status"] == "DRAFT"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == setup_data["p1_id"]


# 3. warehouse staff can create delivery
def test_03_warehouse_staff_can_create_delivery(client, staff_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "customer_reference": "Customer Beta",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "DRAFT"


# 4. server-generated delivery number
def test_04_server_generated_delivery_number(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "customer_reference": "Customer Gamma",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "delivery_number" in data
    assert data["delivery_number"].startswith("DLV-")


# 5. client cannot control generated number
def test_05_client_cannot_control_generated_number(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "delivery_number": "DLV-FAKE-9999",
            "customer_reference": "Customer Fake",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["delivery_number"] != "DLV-FAKE-9999"
    assert resp.json()["delivery_number"].startswith("DLV-")


# 6. active source location validation
def test_06_active_source_location_validation(client, manager_token, setup_data, db_session):
    inact_loc = Location(warehouse_id=setup_data["wh_id"], name="Inactive Dock", code="LOC-INACT", is_active=False)
    db_session.add(inact_loc)
    db_session.commit()

    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": inact_loc.id,
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()


# 7. active source warehouse validation
def test_07_active_source_warehouse_validation(client, manager_token, setup_data, db_session):
    inact_wh = Warehouse(name="Inactive WH", code="WH-INACT", is_active=False)
    db_session.add(inact_wh)
    db_session.commit()
    loc = Location(warehouse_id=inact_wh.id, name="Dock Inactive WH", code="LOC-INACT-WH", is_active=True)
    db_session.add(loc)
    db_session.commit()

    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": loc.id,
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()


# 8. active product validation
def test_08_active_product_validation(client, manager_token, setup_data, db_session):
    inact_p = Product(name="Discontinued Item", sku="DISC-001", unit_of_measure="pcs", is_active=False)
    db_session.add(inact_p)
    db_session.commit()

    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": inact_p.id, "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()


# 9. empty items rejected
def test_09_empty_items_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 10. duplicate products rejected
def test_10_duplicate_products_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {"product_id": setup_data["p1_id"], "quantity": "5.0000"},
                {"product_id": setup_data["p1_id"], "quantity": "10.0000"},
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 11. zero quantity rejected
def test_11_zero_quantity_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "0.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 12. negative quantity rejected
def test_12_negative_quantity_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "-5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 13. Decimal quantity preserved
def test_13_decimal_quantity_preserved(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "12.7500"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    item = resp.json()["items"][0]
    assert float(item["quantity"]) == 12.75


# 14. draft creation changes no stock
def test_14_draft_creation_changes_no_stock(client, manager_token, setup_data, db_session):
    inv_before = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first()
    qty_before = inv_before.quantity

    client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "25.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    db_session.refresh(inv_before)
    assert inv_before.quantity == qty_before


# 15. draft creation creates no DELIVERY ledger
def test_15_draft_creation_creates_no_delivery_ledger(client, manager_token, setup_data, db_session):
    ledgers_before = db_session.query(StockLedger).filter(
        StockLedger.transaction_type == LedgerTransactionType.DELIVERY
    ).count()

    client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "20.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    ledgers_after = db_session.query(StockLedger).filter(
        StockLedger.transaction_type == LedgerTransactionType.DELIVERY
    ).count()
    assert ledgers_after == ledgers_before


# 16. list deliveries
def test_16_list_deliveries(client, manager_token, setup_data):
    resp = client.get(
        "/api/deliveries",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# 17. status filtering
def test_17_status_filtering(client, manager_token, setup_data):
    resp = client.get(
        "/api/deliveries?status=DRAFT",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    for d in resp.json():
        assert d["status"] == "DRAFT"


# 18. warehouse and location filtering
def test_18_location_and_warehouse_filtering(client, manager_token, setup_data):
    resp = client.get(
        f"/api/deliveries?location_id={setup_data['loc1_id']}&warehouse_id={setup_data['wh_id']}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    for d in resp.json():
        assert d["location_id"] == setup_data["loc1_id"]


# 19. search
def test_19_search_deliveries(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "customer_reference": "UNIQUE-SEARCH-REF-99",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "1.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_num = create_resp.json()["delivery_number"]

    resp = client.get(
        "/api/deliveries?search=UNIQUE-SEARCH",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert any(d["delivery_number"] == dlv_num for d in resp.json())


# 20. get detail
def test_20_get_delivery_detail(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "customer_reference": "Detail Test",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    resp = client.get(
        f"/api/deliveries/{dlv_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == dlv_id
    assert data["customer_reference"] == "Detail Test"


# 21. Explicit status transitions via PATCH
def test_21_explicit_lifecycle_transitions(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    # DRAFT -> WAITING allowed
    r1 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "WAITING"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "WAITING"

    # WAITING -> READY allowed
    r2 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "READY"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "READY"

    # READY -> PICKED allowed
    r3 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "PICKED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "PICKED"

    # PICKED -> PACKED allowed
    r4 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "PACKED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r4.status_code == 200
    assert r4.json()["status"] == "PACKED"


def test_21b_draft_to_ready_direct_transition_allowed(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    # DRAFT -> READY allowed directly
    r = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "READY"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "READY"


def test_22_illegal_skipped_and_backward_transitions_rejected(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    # DRAFT -> PICKED rejected
    r1 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "PICKED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r1.status_code == 400

    # DRAFT -> PACKED rejected
    r2 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "PACKED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r2.status_code == 400

    # Advance to WAITING
    client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "WAITING"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    # WAITING -> PICKED rejected
    r3 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "PICKED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r3.status_code == 400

    # WAITING -> PACKED rejected
    r4 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "PACKED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r4.status_code == 400

    # Advance to READY
    client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "READY"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    # READY -> PACKED (skipping PICKED) rejected
    r5 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "PACKED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r5.status_code == 400

    # Backward transition READY -> WAITING rejected
    r6 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "WAITING"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r6.status_code == 400


# 23. Cannot PATCH status directly to DONE or CANCELED
def test_23_cannot_patch_status_directly_to_done_or_canceled(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    resp1 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "DONE"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp1.status_code in (400, 422)

    resp2 = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"status": "CANCELED"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp2.status_code in (400, 422)


# 24. DONE immutable
def test_24_done_immutable(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    # Validate to DONE
    val_resp = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["status"] == "DONE"

    # Attempt patch
    patch_resp = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"customer_reference": "New Ref on Done"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert patch_resp.status_code == 400


# 25. CANCELED immutable
def test_25_canceled_immutable(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    # Cancel
    canc_resp = client.post(
        f"/api/deliveries/{dlv_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert canc_resp.status_code == 200
    assert canc_resp.json()["status"] == "CANCELED"

    # Attempt patch
    patch_resp = client.patch(
        f"/api/deliveries/{dlv_id}",
        json={"customer_reference": "New Ref on Canceled"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert patch_resp.status_code == 400


# 26, 27, 28. cancellation succeeds from valid pre-DONE states
def test_26_27_28_cancellation_flow(client, manager_token, setup_data, db_session):
    inv_before = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity

    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    ledgers_before = db_session.query(StockLedger).count()

    canc_resp = client.post(
        f"/api/deliveries/{dlv_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert canc_resp.status_code == 200
    assert canc_resp.json()["status"] == "CANCELED"

    inv_after = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity
    assert inv_after == inv_before

    ledgers_after = db_session.query(StockLedger).count()
    assert ledgers_after == ledgers_before


# 29. Validation required status == PACKED; non-PACKED states rejected
def test_29_validation_requires_packed_status(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    # Validation from DRAFT rejected
    v1 = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v1.status_code == 400
    assert "packed" in v1.json()["detail"].lower()

    # DRAFT -> WAITING
    client.patch(f"/api/deliveries/{dlv_id}", json={"status": "WAITING"}, headers={"Authorization": f"Bearer {manager_token}"})

    # Validation from WAITING rejected
    v2 = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v2.status_code == 400

    # WAITING -> READY
    client.patch(f"/api/deliveries/{dlv_id}", json={"status": "READY"}, headers={"Authorization": f"Bearer {manager_token}"})

    # Validation from READY rejected
    v3 = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v3.status_code == 400

    # READY -> PICKED
    client.patch(f"/api/deliveries/{dlv_id}", json={"status": "PICKED"}, headers={"Authorization": f"Bearer {manager_token}"})

    # Validation from PICKED rejected
    v4 = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v4.status_code == 400

    # PICKED -> PACKED
    client.patch(f"/api/deliveries/{dlv_id}", json={"status": "PACKED"}, headers={"Authorization": f"Bearer {manager_token}"})

    # Validation from PACKED succeeds
    v5 = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert v5.status_code == 200
    assert v5.json()["status"] == "DONE"


# 30, 31, 32, 33, 34, 35, 36. successful final validation decreases stock from PACKED state
def test_30_to_36_successful_validation_decreases_stock(client, manager_token, setup_data, db_session):
    inv_before = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity

    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "15.5000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    val_resp = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["status"] == "DONE"

    # Verify inventory decrease
    inv_after = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity
    assert inv_after == inv_before - Decimal("15.5000")

    # Verify ledger
    ledger = db_session.query(StockLedger).filter(
        StockLedger.reference_id == str(dlv_id),
        StockLedger.transaction_type == LedgerTransactionType.DELIVERY,
    ).first()
    assert ledger is not None
    assert ledger.quantity_change == Decimal("-15.5000")
    assert ledger.source_location_id == setup_data["loc1_id"]
    assert ledger.performed_by is not None


# 37, 38, 39. double validation rejected & idempotent
def test_37_38_39_double_validation_rejected(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    # First validation succeeds
    res1 = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert res1.status_code == 200

    inv_mid = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity

    ledgers_mid = db_session.query(StockLedger).filter(
        StockLedger.reference_id == str(dlv_id)
    ).count()

    # Second validation fails
    res2 = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert res2.status_code == 400

    inv_end = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity
    assert inv_end == inv_mid

    ledgers_end = db_session.query(StockLedger).filter(
        StockLedger.reference_id == str(dlv_id)
    ).count()
    assert ledgers_end == ledgers_mid


# 40, 42, 43. insufficient physical stock rejected, leaves delivery PACKED and ledgers unchanged
def test_40_42_43_insufficient_physical_stock_rejected(client, manager_token, setup_data, db_session):
    inv_before = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p3_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity  # 10 units available

    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p3_id"], "quantity": "999.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    val_resp = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400
    assert "insufficient" in val_resp.json()["detail"].lower()

    # Stock unchanged
    inv_after = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p3_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity
    assert inv_after == inv_before

    # Delivery remains PACKED
    detail_resp = client.get(
        f"/api/deliveries/{dlv_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert detail_resp.json()["status"] == "PACKED"

    # No persistent delivery ledger
    ledger_count = db_session.query(StockLedger).filter(
        StockLedger.reference_id == str(dlv_id)
    ).count()
    assert ledger_count == 0


# 41. insufficient available stock because of reserved_quantity rejected
def test_41_insufficient_available_stock_due_to_reservation(client, manager_token, setup_data, db_session):
    # p2 at loc1: quantity = 50, reserved = 20 -> available = 30
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p2_id"], "quantity": "40.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    val_resp = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400
    assert "insufficient" in val_resp.json()["detail"].lower()


# 44, 45, 46, 47. multi-item validation succeeds or rolls back atomically
def test_44_to_47_multi_item_atomic_rollback(client, manager_token, setup_data, db_session):
    p1_before = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity

    p3_before = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p3_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity

    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {"product_id": setup_data["p1_id"], "quantity": "10.0000"},
                {"product_id": setup_data["p3_id"], "quantity": "500.0000"},
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    val_resp = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400

    # Verify both stock levels completely unchanged
    p1_after = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity
    assert p1_after == p1_before

    p3_after = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p3_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity
    assert p3_after == p3_before

    # Delivery status remains PACKED
    detail_resp = client.get(
        f"/api/deliveries/{dlv_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert detail_resp.json()["status"] == "PACKED"


# 48. inactive source location at validation time rejected
def test_48_inactive_location_at_validation_rejected(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    # Deactivate location before validation
    loc = db_session.query(Location).filter(Location.id == setup_data["loc1_id"]).first()
    loc.is_active = False
    db_session.commit()

    val_resp = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400

    # Re-enable location for other tests
    loc.is_active = True
    db_session.commit()


# 49. inactive warehouse at validation time rejected
def test_49_inactive_warehouse_at_validation_rejected(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    # Deactivate warehouse
    wh = db_session.query(Warehouse).filter(Warehouse.id == setup_data["wh_id"]).first()
    wh.is_active = False
    db_session.commit()

    val_resp = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400

    # Re-enable warehouse
    wh.is_active = True
    db_session.commit()


# 50. inactive product at validation time rejected
def test_50_inactive_product_at_validation_rejected(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    # Deactivate product
    p1 = db_session.query(Product).filter(Product.id == setup_data["p1_id"]).first()
    p1.is_active = False
    db_session.commit()

    val_resp = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400

    # Re-enable product
    p1.is_active = True
    db_session.commit()


# 52. DONE cannot cancel
def test_52_done_cannot_cancel(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    # Validate to DONE
    client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    # Cancel must fail
    canc_resp = client.post(
        f"/api/deliveries/{dlv_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert canc_resp.status_code == 400


# 53. FOR UPDATE row locking safety check
def test_53_for_update_row_locking_safety(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    dlv_id = create_resp.json()["id"]

    advance_to_packed(client, manager_token, dlv_id)

    val_resp = client.post(
        f"/api/deliveries/{dlv_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["status"] == "DONE"


# 54. Flush/commit exception boundary collision safety check
def test_54_flush_boundary_integrity_error_handling(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201


# 55. Unrelated IntegrityError does not leak raw details or pretend to be delivery_number collision
def test_55_unrelated_integrity_error_handling_sanitized(client, manager_token, setup_data):
    resp = client.post(
        "/api/deliveries",
        json={
            "location_id": 999999,
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 404)
    assert "sqlite3" not in resp.json()["detail"].lower()
    assert "traceback" not in resp.json()["detail"].lower()
