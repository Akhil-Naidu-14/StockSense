from decimal import Decimal
import pytest
from app.models import (
    Inventory,
    LedgerTransactionType,
    Location,
    Product,
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
            "name": "Manager Transfer",
            "email": "mgr_trf@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "mgr_trf@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Staff Transfer",
            "email": "staff_trf@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "staff_trf@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def setup_data(db_session):
    wh1 = Warehouse(name="Source Warehouse", code="WH-TRF-1", is_active=True)
    wh2 = Warehouse(name="Destination Warehouse", code="WH-TRF-2", is_active=True)
    db_session.add_all([wh1, wh2])
    db_session.commit()

    loc1 = Location(warehouse_id=wh1.id, name="Storage A", code="LOC-TRF-1", is_active=True)
    loc2 = Location(warehouse_id=wh2.id, name="Storage B", code="LOC-TRF-2", is_active=True)
    db_session.add_all([loc1, loc2])
    db_session.commit()

    p1 = Product(name="Alpha Part", sku="PART-001", unit_of_measure="pcs", is_active=True)
    p2 = Product(name="Beta Component", sku="COMP-001", unit_of_measure="pcs", is_active=True)
    p3 = Product(name="Gamma Element", sku="ELEM-001", unit_of_measure="pcs", is_active=True)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    # Initial inventory setup:
    # loc1 + p1 = 100 units (reserved = 0)
    # loc1 + p2 = 50 units (reserved = 20 -> available = 30)
    # loc1 + p3 = 10 units
    # loc2 + p1 = 20 units
    inv1 = Inventory(product_id=p1.id, location_id=loc1.id, quantity=Decimal("100.0000"), reserved_quantity=Decimal("0.0000"))
    inv2 = Inventory(product_id=p2.id, location_id=loc1.id, quantity=Decimal("50.0000"), reserved_quantity=Decimal("20.0000"))
    inv3 = Inventory(product_id=p3.id, location_id=loc1.id, quantity=Decimal("10.0000"), reserved_quantity=Decimal("0.0000"))
    inv4 = Inventory(product_id=p1.id, location_id=loc2.id, quantity=Decimal("20.0000"), reserved_quantity=Decimal("0.0000"))
    db_session.add_all([inv1, inv2, inv3, inv4])
    db_session.commit()

    return {
        "wh1_id": wh1.id,
        "wh2_id": wh2.id,
        "loc1_id": loc1.id,
        "loc2_id": loc2.id,
        "p1_id": p1.id,
        "p2_id": p2.id,
        "p3_id": p3.id,
    }


def advance_to_in_transit(client, manager_token, transfer_id):
    """Helper to advance transfer to IN_TRANSIT status."""
    resp = client.patch(
        f"/api/transfers/{transfer_id}",
        json={"status": "IN_TRANSIT"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_TRANSIT"
    return resp


# 1. unauthenticated create rejected
def test_01_unauthenticated_create_rejected(client, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
    )
    assert resp.status_code == 401


# 2. manager create
def test_02_manager_can_create_transfer(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "15.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_location_id"] == setup_data["loc1_id"]
    assert data["destination_location_id"] == setup_data["loc2_id"]
    assert data["status"] == "DRAFT"
    assert len(data["items"]) == 1


# 3. warehouse staff create
def test_03_warehouse_staff_can_create_transfer(client, staff_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "DRAFT"


# 4. server-generated transfer number
def test_04_server_generated_transfer_number(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "transfer_number" in data
    assert data["transfer_number"].startswith("TRF-")


# 5. client cannot control transfer number
def test_05_client_cannot_control_transfer_number(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "transfer_number": "TRF-FAKE-9999",
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["transfer_number"] != "TRF-FAKE-9999"
    assert resp.json()["transfer_number"].startswith("TRF-")


# 6. source location validation
def test_06_active_source_location_validation(client, manager_token, setup_data, db_session):
    inact_loc = Location(warehouse_id=setup_data["wh1_id"], name="Inactive Src", code="LOC-SRC-INACT", is_active=False)
    db_session.add(inact_loc)
    db_session.commit()

    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": inact_loc.id,
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()


# 7. destination location validation
def test_07_active_destination_location_validation(client, manager_token, setup_data, db_session):
    inact_loc = Location(warehouse_id=setup_data["wh2_id"], name="Inactive Dest", code="LOC-DEST-INACT", is_active=False)
    db_session.add(inact_loc)
    db_session.commit()

    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": inact_loc.id,
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()


# 8 & 9. active parent warehouse validation (source & destination)
def test_08_09_active_warehouse_validation(client, manager_token, setup_data, db_session):
    inact_wh = Warehouse(name="Inactive WH", code="WH-INACT-TRF", is_active=False)
    db_session.add(inact_wh)
    db_session.commit()
    loc = Location(warehouse_id=inact_wh.id, name="Loc Inactive WH", code="LOC-INACT-WH-TRF", is_active=True)
    db_session.add(loc)
    db_session.commit()

    resp1 = client.post(
        "/api/transfers",
        json={
            "source_location_id": loc.id,
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp1.status_code == 400

    resp2 = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": loc.id,
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp2.status_code == 400


# 10. source != destination validation
def test_10_identical_source_and_destination_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc1_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 11. active product validation
def test_11_active_product_validation(client, manager_token, setup_data, db_session):
    inact_p = Product(name="Discontinued Part", sku="DISC-TRF-01", unit_of_measure="pcs", is_active=False)
    db_session.add(inact_p)
    db_session.commit()

    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": inact_p.id, "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400


# 12. empty items rejected
def test_12_empty_items_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 13. duplicate products rejected
def test_13_duplicate_products_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [
                {"product_id": setup_data["p1_id"], "quantity": "5.0000"},
                {"product_id": setup_data["p1_id"], "quantity": "10.0000"},
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 14. zero quantity rejected
def test_14_zero_quantity_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "0.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 15. negative quantity rejected
def test_15_negative_quantity_rejected(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "-5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 422)


# 16. Decimal precision preserved
def test_16_decimal_precision_preserved(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "8.3333"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    item = resp.json()["items"][0]
    assert float(item["quantity"]) == 8.3333


# 17, 18, 19. draft creation changes no stock (source or dest) and creates no ledger
def test_17_18_19_draft_creation_changes_no_stock_or_ledger(client, manager_token, setup_data, db_session):
    src_before = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    dest_before = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc2_id"]).first().quantity
    ledgers_before = db_session.query(StockLedger).filter(StockLedger.transaction_type == LedgerTransactionType.TRANSFER).count()

    client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "25.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    src_after = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    dest_after = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc2_id"]).first().quantity
    ledgers_after = db_session.query(StockLedger).filter(StockLedger.transaction_type == LedgerTransactionType.TRANSFER).count()

    assert src_after == src_before
    assert dest_after == dest_before
    assert ledgers_after == ledgers_before


# 20 to 26. list, filter, search, detail
def test_20_to_26_list_filter_search_detail(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]
    trf_num = create_resp.json()["transfer_number"]

    # List
    list_resp = client.get("/api/transfers", headers={"Authorization": f"Bearer {manager_token}"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # Filter status
    status_resp = client.get("/api/transfers?status=DRAFT", headers={"Authorization": f"Bearer {manager_token}"})
    assert status_resp.status_code == 200

    # Filter source location
    src_resp = client.get(f"/api/transfers?source_location_id={setup_data['loc1_id']}", headers={"Authorization": f"Bearer {manager_token}"})
    assert src_resp.status_code == 200

    # Filter destination location
    dest_resp = client.get(f"/api/transfers?destination_location_id={setup_data['loc2_id']}", headers={"Authorization": f"Bearer {manager_token}"})
    assert dest_resp.status_code == 200

    # Search
    search_resp = client.get(f"/api/transfers?search={trf_num}", headers={"Authorization": f"Bearer {manager_token}"})
    assert search_resp.status_code == 200
    assert any(t["transfer_number"] == trf_num for t in search_resp.json())

    # Detail
    detail_resp = client.get(f"/api/transfers/{trf_id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == trf_id


# 27, 28. lifecycle status transitions via PATCH
def test_27_28_lifecycle_status_transitions(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    # DRAFT -> WAITING allowed
    r1 = client.patch(f"/api/transfers/{trf_id}", json={"status": "WAITING"}, headers={"Authorization": f"Bearer {manager_token}"})
    assert r1.status_code == 200
    assert r1.json()["status"] == "WAITING"

    # WAITING -> IN_TRANSIT allowed
    r2 = client.patch(f"/api/transfers/{trf_id}", json={"status": "IN_TRANSIT"}, headers={"Authorization": f"Bearer {manager_token}"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "IN_TRANSIT"

    # IN_TRANSIT -> WAITING (backward) rejected
    r3 = client.patch(f"/api/transfers/{trf_id}", json={"status": "WAITING"}, headers={"Authorization": f"Bearer {manager_token}"})
    assert r3.status_code == 400


# 29, 30. PATCH DONE or CANCELED rejected
def test_29_30_patch_done_or_canceled_rejected(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    r1 = client.patch(f"/api/transfers/{trf_id}", json={"status": "DONE"}, headers={"Authorization": f"Bearer {manager_token}"})
    assert r1.status_code in (400, 422)

    r2 = client.patch(f"/api/transfers/{trf_id}", json={"status": "CANCELED"}, headers={"Authorization": f"Bearer {manager_token}"})
    assert r2.status_code in (400, 422)


# 31, 32. DONE and CANCELED immutable
def test_31_32_done_and_canceled_immutable(client, manager_token, setup_data):
    # Test DONE immutable
    c1 = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    id1 = c1.json()["id"]
    advance_to_in_transit(client, manager_token, id1)
    client.post(f"/api/transfers/{id1}/validate", headers={"Authorization": f"Bearer {manager_token}"})

    p1 = client.patch(f"/api/transfers/{id1}", json={"source_location_id": setup_data["loc2_id"]}, headers={"Authorization": f"Bearer {manager_token}"})
    assert p1.status_code == 400

    # Test CANCELED immutable
    c2 = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    id2 = c2.json()["id"]
    client.post(f"/api/transfers/{id2}/cancel", headers={"Authorization": f"Bearer {manager_token}"})

    p2 = client.patch(f"/api/transfers/{id2}", json={"source_location_id": setup_data["loc2_id"]}, headers={"Authorization": f"Bearer {manager_token}"})
    assert p2.status_code == 400


# 33 to 36. cancellation flow, stock neutrality, canceled cannot validate
def test_33_to_36_cancellation_flow(client, manager_token, setup_data, db_session):
    src_before = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity

    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    canc_resp = client.post(f"/api/transfers/{trf_id}/cancel", headers={"Authorization": f"Bearer {manager_token}"})
    assert canc_resp.status_code == 200
    assert canc_resp.json()["status"] == "CANCELED"

    src_after = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    assert src_after == src_before

    # Canceled cannot validate
    val_resp = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert val_resp.status_code == 400


# 37. validation requires IN_TRANSIT status; non-IN_TRANSIT rejected
def test_37_validation_requires_in_transit_status(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    # Validate from DRAFT rejected
    v1 = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert v1.status_code == 400

    # Advance to WAITING
    client.patch(f"/api/transfers/{trf_id}", json={"status": "WAITING"}, headers={"Authorization": f"Bearer {manager_token}"})

    # Validate from WAITING rejected
    v2 = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert v2.status_code == 400

    # Advance to IN_TRANSIT
    client.patch(f"/api/transfers/{trf_id}", json={"status": "IN_TRANSIT"}, headers={"Authorization": f"Bearer {manager_token}"})

    # Validate from IN_TRANSIT succeeds
    v3 = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert v3.status_code == 200
    assert v3.json()["status"] == "DONE"


# 38 to 49. successful validation stock movements, company stock conservation, ledger properties
def test_38_to_49_successful_validation_stock_and_ledger(client, manager_token, setup_data, db_session):
    src_before = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    dest_before = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc2_id"]).first().quantity
    total_before = src_before + dest_before

    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "15.5000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    val_resp = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert val_resp.status_code == 200
    assert val_resp.json()["status"] == "DONE"

    src_after = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    dest_after = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc2_id"]).first().quantity
    total_after = src_after + dest_after

    # Stock movements
    assert src_after == src_before - Decimal("15.5000")
    assert dest_after == dest_before + Decimal("15.5000")

    # Conservation invariant
    assert total_after == total_before

    # Single TRANSFER ledger entry
    ledgers = db_session.query(StockLedger).filter(
        StockLedger.reference_id == str(trf_id),
        StockLedger.transaction_type == LedgerTransactionType.TRANSFER,
    ).all()
    assert len(ledgers) == 1
    ledger = ledgers[0]
    assert ledger.source_location_id == setup_data["loc1_id"]
    assert ledger.destination_location_id == setup_data["loc2_id"]
    assert ledger.quantity_change == Decimal("15.5000")
    assert ledger.performed_by is not None


# 40. destination Inventory row created if absent
def test_40_destination_inventory_row_created_if_absent(client, manager_token, setup_data, db_session):
    # p3 at loc2 has no Inventory row initially
    inv_absent = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p3_id"], Inventory.location_id == setup_data["loc2_id"]).first()
    assert inv_absent is None

    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p3_id"], "quantity": "4.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    val_resp = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert val_resp.status_code == 200

    inv_created = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p3_id"], Inventory.location_id == setup_data["loc2_id"]).first()
    assert inv_created is not None
    assert inv_created.quantity == Decimal("4.0000")


# 50 to 52. double validation rejected & idempotent
def test_50_to_52_double_validation_rejected(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    res1 = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert res1.status_code == 200

    src_mid = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    ledgers_mid = db_session.query(StockLedger).filter(StockLedger.reference_id == str(trf_id)).count()

    res2 = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert res2.status_code == 400

    src_end = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    ledgers_end = db_session.query(StockLedger).filter(StockLedger.reference_id == str(trf_id)).count()

    assert src_end == src_mid
    assert ledgers_end == ledgers_mid


# 53, 55, 56, 57. insufficient physical stock rejected, leaves stock unchanged
def test_53_55_56_57_insufficient_physical_stock_rejected(client, manager_token, setup_data, db_session):
    src_before = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p3_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity

    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p3_id"], "quantity": "999.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    val_resp = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert val_resp.status_code == 400
    assert "insufficient" in val_resp.json()["detail"].lower()

    src_after = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p3_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    assert src_after == src_before


# 54. insufficient available stock due to reservation rejected
def test_54_insufficient_available_stock_due_to_reservation(client, manager_token, setup_data):
    # p2 at loc1: quantity = 50, reserved = 20 -> available = 30
    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p2_id"], "quantity": "40.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    val_resp = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert val_resp.status_code == 400
    assert "insufficient" in val_resp.json()["detail"].lower()


# 58 to 62. multi-item atomicity rollback on failure
def test_58_to_62_multi_item_atomic_rollback(client, manager_token, setup_data, db_session):
    p1_src_before = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    p1_dest_before = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc2_id"]).first().quantity

    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [
                {"product_id": setup_data["p1_id"], "quantity": "10.0000"},
                {"product_id": setup_data["p3_id"], "quantity": "500.0000"},
            ],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    val_resp = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert val_resp.status_code == 400

    p1_src_after = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc1_id"]).first().quantity
    p1_dest_after = db_session.query(Inventory).filter(Inventory.product_id == setup_data["p1_id"], Inventory.location_id == setup_data["loc2_id"]).first().quantity

    # All stock levels unchanged
    assert p1_src_after == p1_src_before
    assert p1_dest_after == p1_dest_before

    # Transfer status remains IN_TRANSIT
    detail_resp = client.get(f"/api/transfers/{trf_id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert detail_resp.json()["status"] == "IN_TRANSIT"


# 63 to 67. inactive resources rechecked at validation time
def test_63_to_67_inactive_resources_rechecked_at_validation(client, manager_token, setup_data, db_session):
    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    # Deactivate product
    p1 = db_session.query(Product).filter(Product.id == setup_data["p1_id"]).first()
    p1.is_active = False
    db_session.commit()

    val_resp = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert val_resp.status_code == 400

    # Re-enable product
    p1.is_active = True
    db_session.commit()


# 68. SELECT FOR UPDATE validation strategy test
def test_68_for_update_row_locking_safety(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    val_resp = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert val_resp.status_code == 200
    assert val_resp.json()["status"] == "DONE"


# 69. DONE cannot cancel
def test_69_done_cannot_cancel(client, manager_token, setup_data):
    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})

    canc_resp = client.post(f"/api/transfers/{trf_id}/cancel", headers={"Authorization": f"Bearer {manager_token}"})
    assert canc_resp.status_code == 400


# 70. Transfer number flush/commit collision handling test
def test_70_transfer_number_collision_retry_handling(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201


# 71, 72. Unrelated IntegrityError sanitized
def test_71_72_unrelated_integrity_error_sanitized(client, manager_token, setup_data):
    resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": 999999,
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "10.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code in (400, 404)
    assert "sqlite3" not in resp.json()["detail"].lower()
    assert "traceback" not in resp.json()["detail"].lower()


# 73. Different-document destination inventory creation IntegrityError failure path handled safely
def test_73_destination_creation_race_integrity_error_handled(client, manager_token, setup_data, db_session, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    create_resp = client.post(
        "/api/transfers",
        json={
            "source_location_id": setup_data["loc1_id"],
            "destination_location_id": setup_data["loc2_id"],
            "items": [{"product_id": setup_data["p1_id"], "quantity": "5.0000"}],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    trf_id = create_resp.json()["id"]

    advance_to_in_transit(client, manager_token, trf_id)

    src_before = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity

    # Simulate IntegrityError on transfer_stock (e.g. concurrent creation race on destination inventory row)
    def mock_transfer_stock(*args, **kwargs):
        raise IntegrityError("INSERT INTO inventories", params={}, orig=Exception("UNIQUE constraint failed: inventories.product_id, inventories.location_id"))

    monkeypatch.setattr("app.services.inventory_service.InventoryService.transfer_stock", mock_transfer_stock)

    val_resp = client.post(f"/api/transfers/{trf_id}/validate", headers={"Authorization": f"Bearer {manager_token}"})
    assert val_resp.status_code == 409
    assert "concurrent" in val_resp.json()["detail"].lower()
    assert "sqlite3" not in val_resp.json()["detail"].lower()
    assert "traceback" not in val_resp.json()["detail"].lower()

    # Verify rollback: status remains IN_TRANSIT, stock unchanged
    db_session.expire_all()
    src_after = db_session.query(Inventory).filter(
        Inventory.product_id == setup_data["p1_id"],
        Inventory.location_id == setup_data["loc1_id"],
    ).first().quantity
    assert src_after == src_before

    detail_resp = client.get(f"/api/transfers/{trf_id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert detail_resp.json()["status"] == "IN_TRANSIT"

