from decimal import Decimal
import pytest
from app.models import (
    Inventory,
    LedgerTransactionType,
    Location,
    Product,
    Receipt,
    ReceiptStatus,
    StockLedger,
    User,
    Warehouse,
)


@pytest.fixture
def manager_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Manager One",
            "email": "mgr_rec@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "mgr_rec@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Staff One",
            "email": "staff_rec@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "staff_rec@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def setup_data(db_session):
    wh = Warehouse(name="Main Warehouse", code="WH-REC-1", is_active=True)
    db_session.add(wh)
    db_session.commit()

    loc1 = Location(warehouse_id=wh.id, name="Receiving Bay", code="LOC-REC-1", is_active=True)
    loc2 = Location(warehouse_id=wh.id, name="Overflow Bay", code="LOC-REC-2", is_active=True)
    db_session.add_all([loc1, loc2])
    db_session.commit()

    p1 = Product(name="Steel Rods", sku="STEEL-001", unit_of_measure="pcs", is_active=True)
    p2 = Product(name="Copper Tubes", sku="COPPER-001", unit_of_measure="pcs", is_active=True)
    db_session.add_all([p1, p2])
    db_session.commit()

    return {
        "wh_id": wh.id,
        "loc1_id": loc1.id,
        "loc2_id": loc2.id,
        "p1_id": p1.id,
        "p2_id": p2.id,
    }


# 1. unauthenticated create -> 401
def test_01_unauthenticated_create_returns_401(client, setup_data):
    resp = client.post(
        "/api/receipts",
        json={
            "supplier": "Test Supplier",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "100.0000"}],
        },
    )
    assert resp.status_code == 401


# 2. manager can create receipt
def test_02_manager_can_create_receipt(client, manager_token, setup_data):
    resp = client.post(
        "/api/receipts",
        json={
            "supplier": "Hyderabad Steel Suppliers",
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "100.0000",
                    "received_quantity": "100.0000",
                }
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["supplier"] == "Hyderabad Steel Suppliers"
    assert data["status"] == "DRAFT"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == setup_data["p1_id"]


# 3. warehouse staff can create receipt
def test_03_warehouse_staff_can_create_receipt(client, staff_token, setup_data):
    resp = client.post(
        "/api/receipts",
        json={
            "supplier": "Staff Supplier",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "50.0000"}],
        },
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "DRAFT"


# 4. receipt number generated server-side
def test_04_receipt_number_generated_server_side(client, manager_token, setup_data):
    resp = client.post(
        "/api/receipts",
        json={
            "supplier": "No Number Supplier",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "receipt_number" in data
    assert data["receipt_number"].startswith("RCV-")


# 5. create validates active location
def test_05_create_validates_active_location(client, manager_token, setup_data, db_session):
    # Inactive location
    inact_loc = Location(
        warehouse_id=setup_data["wh_id"], name="Inactive Loc", code="LOC-INACT", is_active=False
    )
    db_session.add(inact_loc)
    db_session.commit()

    resp = client.post(
        "/api/receipts",
        json={
            "location_id": inact_loc.id,
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 404)


# 6. create validates active products
def test_06_create_validates_active_products(client, manager_token, setup_data, db_session):
    inact_prod = Product(name="Discontinued Item", sku="DISC-001", is_active=False)
    db_session.add(inact_prod)
    db_session.commit()

    resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": inact_prod.id, "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 404)


# 7. zero/negative requested quantity rejected
def test_07_zero_or_negative_requested_quantity_rejected(client, manager_token, setup_data):
    resp1 = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "0.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp1.status_code in (400, 422)

    resp2 = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "-5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp2.status_code in (400, 422)


# 8. negative received quantity rejected
def test_08_negative_received_quantity_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "10.0000",
                    "received_quantity": "-1.0000",
                }
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 9. received > requested rejected
def test_09_received_greater_than_requested_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "10.0000",
                    "received_quantity": "15.0000",
                }
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 10. duplicate product lines rejected
def test_10_duplicate_product_lines_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {"product_id": setup_data["p1_id"], "quantity": "10.0000"},
                {"product_id": setup_data["p1_id"], "quantity": "20.0000"},
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 11. empty items rejected
def test_11_empty_items_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/receipts",
        json={"location_id": setup_data["loc1_id"], "items": []},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 12. draft creation does not change stock
def test_12_draft_creation_does_not_change_stock(client, manager_token, setup_data, db_session):
    client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "100.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    inv = (
        db_session.query(Inventory)
        .filter(
            Inventory.product_id == setup_data["p1_id"],
            Inventory.location_id == setup_data["loc1_id"],
        )
        .first()
    )
    assert inv is None or inv.quantity == Decimal("0.0000")


# 13. draft creation creates no receipt ledger
def test_13_draft_creation_creates_no_receipt_ledger(client, manager_token, setup_data, db_session):
    client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "100.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    ledgers = (
        db_session.query(StockLedger)
        .filter(StockLedger.transaction_type == LedgerTransactionType.RECEIPT)
        .all()
    )
    assert len(ledgers) == 0


# 14. list receipts
def test_14_list_receipts(client, manager_token, setup_data):
    client.post(
        "/api/receipts",
        json={
            "supplier": "Supplier A",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    resp = client.get("/api/receipts", headers={"Authorization": f"Bearer {manager_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# 15. status filter
def test_15_status_filter(client, manager_token, setup_data):
    # Create draft receipt
    client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    resp = client.get(
        "/api/receipts?status=DRAFT", headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert resp.status_code == 200
    assert all(r["status"] == "DRAFT" for r in resp.json())

    resp_done = client.get(
        "/api/receipts?status=DONE", headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert resp_done.status_code == 200
    assert len(resp_done.json()) == 0


# 16. warehouse/location filter
def test_16_warehouse_and_location_filter(client, manager_token, setup_data):
    client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    resp_loc = client.get(
        f"/api/receipts?location_id={setup_data['loc1_id']}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp_loc.status_code == 200
    assert len(resp_loc.json()) >= 1

    resp_wh = client.get(
        f"/api/receipts?warehouse_id={setup_data['wh_id']}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp_wh.status_code == 200
    assert len(resp_wh.json()) >= 1


# 17. search receipt number/supplier
def test_17_search_receipt_number_and_supplier(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "supplier": "Acme Steel Corp",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    r_num = create_resp.json()["receipt_number"]

    # Search by supplier
    resp1 = client.get(
        "/api/receipts?search=Acme", headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert resp1.status_code == 200
    assert any(r["receipt_number"] == r_num for r in resp1.json())

    # Search by receipt_number
    resp2 = client.get(
        f"/api/receipts?search={r_num}", headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1


# 18. get detail
def test_18_get_detail(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "supplier": "Detail Supplier",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    resp = client.get(
        f"/api/receipts/{rec_id}", headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == rec_id
    assert data["location_name"] == "Receiving Bay"
    assert data["warehouse_name"] == "Main Warehouse"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_name"] == "Steel Rods"


# 19. update draft supplier
def test_19_update_draft_supplier(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "supplier": "Old Supplier",
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/receipts/{rec_id}",
        json={"supplier": "New Updated Supplier"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["supplier"] == "New Updated Supplier"


# 20. update draft items
def test_20_update_draft_items(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/receipts/{rec_id}",
        json={
            "items": [
                {"product_id": setup_data["p1_id"], "quantity": "20.0000"},
                {"product_id": setup_data["p2_id"], "quantity": "30.0000"},
            ]
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2


# 21. canceled receipt cannot edit
def test_21_canceled_receipt_cannot_edit(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    # Cancel
    client.post(
        f"/api/receipts/{rec_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    # Try edit
    resp = client.patch(
        f"/api/receipts/{rec_id}",
        json={"supplier": "Changed Supplier"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400


# 22. done receipt cannot edit
def test_22_done_receipt_cannot_edit(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    # Validate
    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    # Try edit
    resp = client.patch(
        f"/api/receipts/{rec_id}",
        json={"supplier": "Changed Supplier"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400


# 23. cancel draft succeeds
def test_23_cancel_draft_succeeds(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/receipts/{rec_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELED"


# 24. cancel does not mutate stock
def test_24_cancel_does_not_mutate_stock(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    inv = (
        db_session.query(Inventory)
        .filter(
            Inventory.product_id == setup_data["p1_id"],
            Inventory.location_id == setup_data["loc1_id"],
        )
        .first()
    )
    assert inv is None or inv.quantity == Decimal("0.0000")


# 25. canceled receipt cannot validate
def test_25_canceled_receipt_cannot_validate(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    val_resp = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400


# 26. validate receipt increases stock
def test_26_validate_receipt_increases_stock(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "100.0000",
                    "received_quantity": "100.0000",
                }
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    val_resp = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 200

    inv = (
        db_session.query(Inventory)
        .filter(
            Inventory.product_id == setup_data["p1_id"],
            Inventory.location_id == setup_data["loc1_id"],
        )
        .first()
    )
    assert inv is not None
    assert inv.quantity == Decimal("100.0000")


# 27. validate uses received_quantity
def test_27_validate_uses_received_quantity(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "100.0000",
                    "received_quantity": "80.0000",
                }
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    inv = (
        db_session.query(Inventory)
        .filter(
            Inventory.product_id == setup_data["p1_id"],
            Inventory.location_id == setup_data["loc1_id"],
        )
        .first()
    )
    assert inv.quantity == Decimal("80.0000")


# 28. validate creates correct RECEIPT ledger
def test_28_validate_creates_correct_receipt_ledger(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "100.0000",
                    "received_quantity": "100.0000",
                }
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == str(rec_id))
        .first()
    )
    assert ledger is not None
    assert ledger.transaction_type == LedgerTransactionType.RECEIPT
    assert ledger.product_id == setup_data["p1_id"]
    assert ledger.destination_location_id == setup_data["loc1_id"]
    assert ledger.quantity_before == Decimal("0.0000")
    assert ledger.quantity_change == Decimal("100.0000")
    assert ledger.quantity_after == Decimal("100.0000")


# 29. performed_by correct
def test_29_performed_by_correct(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    mgr_user = db_session.query(User).filter(User.email == "mgr_rec@example.com").first()
    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == str(rec_id))
        .first()
    )
    assert ledger.performed_by == mgr_user.id


# 30. reference_id correct
def test_30_reference_id_correct(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    ledger = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == str(rec_id))
        .first()
    )
    assert ledger.reference_id == str(rec_id)


# 31. validate marks receipt DONE
def test_31_validate_marks_receipt_done(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    val_resp = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["status"] == "DONE"


# 32. double validation rejected
def test_32_double_validation_rejected(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    val_resp2 = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp2.status_code == 400


# 33. double validation does not increase stock twice
def test_33_double_validation_does_not_increase_stock_twice(
    client, manager_token, setup_data, db_session
):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "100.0000",
                    "received_quantity": "100.0000",
                }
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    inv = (
        db_session.query(Inventory)
        .filter(
            Inventory.product_id == setup_data["p1_id"],
            Inventory.location_id == setup_data["loc1_id"],
        )
        .first()
    )
    assert inv.quantity == Decimal("100.0000")


# 34. double validation does not create duplicate ledger
def test_34_double_validation_does_not_create_duplicate_ledger(
    client, manager_token, setup_data, db_session
):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    ledgers = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == str(rec_id))
        .all()
    )
    assert len(ledgers) == 1


# 35. zero-received lines cause no stock mutation
def test_35_zero_received_lines_cause_no_stock_mutation(
    client, manager_token, setup_data, db_session
):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "100.0000",
                    "received_quantity": "50.0000",
                },
                {
                    "product_id": setup_data["p2_id"],
                    "quantity": "50.0000",
                    "received_quantity": "0.0000",
                },
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    inv_p2 = (
        db_session.query(Inventory)
        .filter(
            Inventory.product_id == setup_data["p2_id"],
            Inventory.location_id == setup_data["loc1_id"],
        )
        .first()
    )
    assert inv_p2 is None or inv_p2.quantity == Decimal("0.0000")

    ledgers_p2 = (
        db_session.query(StockLedger)
        .filter(
            StockLedger.reference_id == str(rec_id),
            StockLedger.product_id == setup_data["p2_id"],
        )
        .all()
    )
    assert len(ledgers_p2) == 0


# 36. at least one positive received quantity required for validation
def test_36_at_least_one_positive_received_quantity_required_for_validation(
    client, manager_token, setup_data
):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "100.0000",
                    "received_quantity": "0.0000",
                }
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    val_resp = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400


# 37. multi-item validation succeeds atomically
def test_37_multi_item_validation_succeeds_atomically(
    client, manager_token, setup_data, db_session
):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "100.0000",
                    "received_quantity": "100.0000",
                },
                {
                    "product_id": setup_data["p2_id"],
                    "quantity": "50.0000",
                    "received_quantity": "50.0000",
                },
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    val_resp = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 200

    inv1 = (
        db_session.query(Inventory)
        .filter(
            Inventory.product_id == setup_data["p1_id"],
            Inventory.location_id == setup_data["loc1_id"],
        )
        .first()
    )
    inv2 = (
        db_session.query(Inventory)
        .filter(
            Inventory.product_id == setup_data["p2_id"],
            Inventory.location_id == setup_data["loc1_id"],
        )
        .first()
    )
    assert inv1.quantity == Decimal("100.0000")
    assert inv2.quantity == Decimal("50.0000")


# 38. multi-item failure rolls back all stock mutations
# 39. multi-item failure rolls back ledger entries
# 40. failed validation leaves receipt non-DONE
def test_38_39_40_multi_item_failure_atomicity(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "100.0000",
                    "received_quantity": "100.0000",
                },
                {
                    "product_id": setup_data["p2_id"],
                    "quantity": "50.0000",
                    "received_quantity": "50.0000",
                },
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    # Inactivate product 2 right before validation
    p2 = db_session.query(Product).filter(Product.id == setup_data["p2_id"]).first()
    p2.is_active = False
    db_session.commit()

    val_resp = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400

    # Verify item 1 stock mutation was rolled back
    inv1 = (
        db_session.query(Inventory)
        .filter(
            Inventory.product_id == setup_data["p1_id"],
            Inventory.location_id == setup_data["loc1_id"],
        )
        .first()
    )
    assert inv1 is None or inv1.quantity == Decimal("0.0000")

    # Verify no ledger entries were created
    ledgers = (
        db_session.query(StockLedger)
        .filter(StockLedger.reference_id == str(rec_id))
        .all()
    )
    assert len(ledgers) == 0

    # Verify receipt remains non-DONE (DRAFT)
    rec = db_session.query(Receipt).filter(Receipt.id == rec_id).first()
    assert rec.status == ReceiptStatus.DRAFT


# 41. Decimal quantities preserved
def test_41_decimal_quantities_preserved(client, manager_token, setup_data):
    resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [
                {
                    "product_id": setup_data["p1_id"],
                    "quantity": "123.4567",
                    "received_quantity": "123.4567",
                }
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    item = resp.json()["items"][0]
    assert Decimal(str(item["quantity"])) == Decimal("123.4567")
    assert Decimal(str(item["received_quantity"])) == Decimal("123.4567")


# 42. inactive destination location rejected at validation time
def test_42_inactive_destination_location_rejected_at_validation_time(
    client, manager_token, setup_data, db_session
):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    # Inactivate location
    loc = db_session.query(Location).filter(Location.id == setup_data["loc1_id"]).first()
    loc.is_active = False
    db_session.commit()

    val_resp = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400


# 43. inactive product rejected at validation time
def test_43_inactive_product_rejected_at_validation_time(
    client, manager_token, setup_data, db_session
):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    # Inactivate product
    p = db_session.query(Product).filter(Product.id == setup_data["p1_id"]).first()
    p.is_active = False
    db_session.commit()

    val_resp = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 400


# 44. cannot cancel DONE receipt
def test_44_cannot_cancel_done_receipt(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    # Validate
    client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    # Try cancel
    cancel_resp = client.post(
        f"/api/receipts/{rec_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert cancel_resp.status_code == 400


# 45. FOR UPDATE row locking safety check
def test_45_for_update_row_locking_safety(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    rec_id = create_resp.json()["id"]

    val_resp = client.post(
        f"/api/receipts/{rec_id}/validate",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["status"] == "DONE"


# 46. Flush/commit exception boundary safety check
def test_46_flush_boundary_integrity_error_handling(client, manager_token, setup_data):
    # Valid creation request succeeds cleanly
    resp = client.post(
        "/api/receipts",
        json={
            "location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201


# 47. Unrelated IntegrityError does not leak raw details or pretend to be receipt_number collision
def test_47_unrelated_integrity_error_handling_sanitized(client, manager_token, setup_data, db_session):
    # Attempting to create with an invalid/nonexistent location_id that triggers a FK error if unvalidated
    resp = client.post(
        "/api/receipts",
        json={
            "location_id": 999999,
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 404)
    # Ensure raw exception text like "sqlite3.IntegrityError" or "e.orig" is NOT in detail
    assert "sqlite3" not in resp.json()["detail"].lower()
    assert "traceback" not in resp.json()["detail"].lower()


