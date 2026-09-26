from decimal import Decimal
import pytest
from app.models import (
    Category,
    Delivery,
    DeliveryStatus,
    Inventory,
    Location,
    Product,
    Receipt,
    ReceiptStatus,
    Transfer,
    TransferStatus,
    User,
    Warehouse,
)


@pytest.fixture
def manager_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Manager Dash",
            "email": "mgr_dash@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "mgr_dash@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Staff Dash",
            "email": "staff_dash@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "staff_dash@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def setup_dashboard_data(db_session):
    cat = Category(name="Electronics", description="Electronics Category")
    db_session.add(cat)
    db_session.commit()

    wh = Warehouse(name="Dash Warehouse", code="WH-DASH-1", is_active=True)
    db_session.add(wh)
    db_session.commit()

    loc1 = Location(warehouse_id=wh.id, name="Dash Loc 1", code="LOC-DASH-1", is_active=True)
    loc2 = Location(warehouse_id=wh.id, name="Dash Loc 2", code="LOC-DASH-2", is_active=True)
    db_session.add_all([loc1, loc2])
    db_session.commit()

    p1 = Product(name="Smart Phone", sku="PHONE-001", category_id=cat.id, unit_of_measure="pcs", reorder_level=Decimal("10.0000"), reorder_quantity=Decimal("50.0000"), is_active=True)
    p2 = Product(name="Laptop", sku="LAPTOP-001", category_id=cat.id, unit_of_measure="pcs", reorder_level=Decimal("5.0000"), reorder_quantity=Decimal("20.0000"), is_active=True)
    p3_inactive = Product(name="Old Gadget", sku="OLD-001", category_id=cat.id, unit_of_measure="pcs", is_active=False)
    db_session.add_all([p1, p2, p3_inactive])
    db_session.commit()

    inv1 = Inventory(product_id=p1.id, location_id=loc1.id, quantity=Decimal("5.0000"), reserved_quantity=Decimal("0.0000")) # Low stock
    inv2 = Inventory(product_id=p2.id, location_id=loc1.id, quantity=Decimal("0.0000"), reserved_quantity=Decimal("0.0000")) # Out of stock & Low stock
    db_session.add_all([inv1, inv2])
    db_session.commit()

    # Documents
    rcp_draft = Receipt(receipt_number="RCP-DASH-001", location_id=loc1.id, status=ReceiptStatus.DRAFT)
    rcp_done = Receipt(receipt_number="RCP-DASH-002", location_id=loc1.id, status=ReceiptStatus.DONE)

    del_waiting = Delivery(delivery_number="DEL-DASH-001", location_id=loc1.id, status=DeliveryStatus.WAITING)
    del_canceled = Delivery(delivery_number="DEL-DASH-002", location_id=loc1.id, status=DeliveryStatus.CANCELED)

    trf_in_transit = Transfer(transfer_number="TRF-DASH-001", source_location_id=loc1.id, destination_location_id=loc2.id, status=TransferStatus.IN_TRANSIT)
    trf_done = Transfer(transfer_number="TRF-DASH-002", source_location_id=loc1.id, destination_location_id=loc2.id, status=TransferStatus.DONE)

    db_session.add_all([rcp_draft, rcp_done, del_waiting, del_canceled, trf_in_transit, trf_done])
    db_session.commit()

    return {
        "cat_id": cat.id,
        "wh_id": wh.id,
        "loc1_id": loc1.id,
        "loc2_id": loc2.id,
        "p1_id": p1.id,
        "p2_id": p2.id,
    }


def test_auth_and_dashboard_kpi(client, manager_token, staff_token, setup_dashboard_data):
    # Unauthenticated -> 401
    assert client.get("/api/dashboard").status_code == 401

    # Staff access -> 200
    res_staff = client.get("/api/dashboard", headers={"Authorization": f"Bearer {staff_token}"})
    assert res_staff.status_code == 200

    # Manager access -> 200
    res = client.get("/api/dashboard", headers={"Authorization": f"Bearer {manager_token}"})
    assert res.status_code == 200
    kpis = res.json()

    assert kpis["total_products"] >= 2  # p1 and p2 active
    assert kpis["low_stock_items"] >= 2
    assert kpis["out_of_stock_items"] >= 1
    assert kpis["pending_receipts"] >= 1 # rcp_draft included, rcp_done excluded
    assert kpis["pending_deliveries"] >= 1 # del_waiting included, del_canceled excluded
    assert kpis["scheduled_transfers"] >= 1 # trf_in_transit included, trf_done excluded


def test_dashboard_filters(client, manager_token, setup_dashboard_data):
    wh_id = setup_dashboard_data["wh_id"]
    loc1_id = setup_dashboard_data["loc1_id"]
    cat_id = setup_dashboard_data["cat_id"]

    res = client.get(
        f"/api/dashboard?warehouse_id={wh_id}&location_id={loc1_id}&category_id={cat_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert res.status_code == 200
    kpis = res.json()
    assert kpis["total_products"] >= 2
    assert kpis["pending_receipts"] >= 1
    assert kpis["pending_deliveries"] >= 1
