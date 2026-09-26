from decimal import Decimal
import pytest
from app.models import Inventory, Location, Product, ReorderRule, User, Warehouse


@pytest.fixture
def manager_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Manager Reorder",
            "email": "mgr_reorder@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "mgr_reorder@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Staff Reorder",
            "email": "staff_reorder@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "staff_reorder@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def setup_reorder_data(db_session):
    wh = Warehouse(name="Reorder Warehouse", code="WH-RE-1", is_active=True)
    db_session.add(wh)
    db_session.commit()

    loc = Location(warehouse_id=wh.id, name="Reorder Loc", code="LOC-RE-1", is_active=True)
    db_session.add(loc)
    db_session.commit()

    p1 = Product(name="Item One", sku="RE-001", unit_of_measure="pcs", reorder_level=Decimal("10.0000"), reorder_quantity=Decimal("50.0000"), is_active=True)
    p2 = Product(name="Item Two", sku="RE-002", unit_of_measure="pcs", reorder_level=Decimal("5.0000"), reorder_quantity=Decimal("20.0000"), is_active=True)
    db_session.add_all([p1, p2])
    db_session.commit()

    inv1 = Inventory(product_id=p1.id, location_id=loc.id, quantity=Decimal("8.0000"), reserved_quantity=Decimal("0.0000"))
    inv2 = Inventory(product_id=p2.id, location_id=loc.id, quantity=Decimal("0.0000"), reserved_quantity=Decimal("0.0000"))
    db_session.add_all([inv1, inv2])
    db_session.commit()

    return {
        "wh_id": wh.id,
        "loc_id": loc.id,
        "p1_id": p1.id,
        "p2_id": p2.id,
    }


def test_auth_and_rbac(client, manager_token, staff_token, setup_reorder_data):
    p1_id = setup_reorder_data["p1_id"]
    loc_id = setup_reorder_data["loc_id"]

    # Unauthenticated -> 401
    assert client.get("/api/reorder-rules").status_code == 401
    assert client.post("/api/reorder-rules", json={"product_id": p1_id, "minimum_quantity": 10, "reorder_quantity": 50}).status_code == 401

    # Staff write attempt -> 403
    staff_post = client.post(
        "/api/reorder-rules",
        json={"product_id": p1_id, "minimum_quantity": 10, "reorder_quantity": 50},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert staff_post.status_code == 403

    # Staff read -> 200
    staff_get = client.get("/api/reorder-rules", headers={"Authorization": f"Bearer {staff_token}"})
    assert staff_get.status_code == 200

    # Manager write -> 201
    mgr_post = client.post(
        "/api/reorder-rules",
        json={"product_id": p1_id, "location_id": loc_id, "minimum_quantity": 15, "reorder_quantity": 100},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert mgr_post.status_code == 201
    rule_id = mgr_post.json()["id"]

    # Manager update -> 200
    mgr_patch = client.patch(
        f"/api/reorder-rules/{rule_id}",
        json={"minimum_quantity": 20},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert mgr_patch.status_code == 200

    # Manager delete (deactivate) -> 200
    mgr_del = client.delete(
        f"/api/reorder-rules/{rule_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert mgr_del.status_code == 200
    assert mgr_del.json()["active"] is False


def test_invalid_reorder_quantities_and_inactive_resources(client, manager_token, setup_reorder_data, db_session):
    p1_id = setup_reorder_data["p1_id"]
    loc_id = setup_reorder_data["loc_id"]

    # Negative minimum
    r1 = client.post(
        "/api/reorder-rules",
        json={"product_id": p1_id, "minimum_quantity": -5, "reorder_quantity": 50},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r1.status_code == 422 or r1.status_code == 400

    # Zero reorder quantity
    r2 = client.post(
        "/api/reorder-rules",
        json={"product_id": p1_id, "minimum_quantity": 10, "reorder_quantity": 0},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r2.status_code == 422 or r2.status_code == 400

    # Inactive product
    p_inact = Product(name="Inact", sku="INACT-RE", unit_of_measure="pcs", is_active=False)
    db_session.add(p_inact)
    db_session.commit()
    r3 = client.post(
        "/api/reorder-rules",
        json={"product_id": p_inact.id, "minimum_quantity": 10, "reorder_quantity": 50},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert r3.status_code == 400


def test_duplicate_active_rule_rejection(client, manager_token, setup_reorder_data):
    p1_id = setup_reorder_data["p1_id"]
    loc_id = setup_reorder_data["loc_id"]

    # Create first rule for (p1_id, loc_id)
    c1 = client.post(
        "/api/reorder-rules",
        json={"product_id": p1_id, "location_id": loc_id, "minimum_quantity": 10, "reorder_quantity": 50},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert c1.status_code == 201

    # Create duplicate active rule -> 409
    c2 = client.post(
        "/api/reorder-rules",
        json={"product_id": p1_id, "location_id": loc_id, "minimum_quantity": 15, "reorder_quantity": 60},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert c2.status_code == 409


def test_low_stock_and_out_of_stock_endpoints(client, manager_token, setup_reorder_data):
    p1_id = setup_reorder_data["p1_id"]  # available = 8, reorder_level = 10 -> LOW STOCK
    p2_id = setup_reorder_data["p2_id"]  # available = 0 -> OUT OF STOCK & LOW STOCK

    # GET low-stock
    ls_res = client.get("/api/inventory/low-stock", headers={"Authorization": f"Bearer {manager_token}"})
    assert ls_res.status_code == 200
    ls_data = ls_res.json()
    assert len(ls_data) >= 2

    # GET out-of-stock
    os_res = client.get("/api/inventory/out-of-stock", headers={"Authorization": f"Bearer {manager_token}"})
    assert os_res.status_code == 200
    os_data = os_res.json()
    assert any(item["product_id"] == p2_id for item in os_data)

    # Verify no inventory rows were mutated or created by query
    ls_res2 = client.get("/api/inventory/low-stock", headers={"Authorization": f"Bearer {manager_token}"})
    assert len(ls_res2.json()) == len(ls_data)


def test_precedence_location_rule_over_product_rule_over_product_default(client, manager_token, setup_reorder_data):
    """
    Location-specific rule > Product-wide rule > Product.reorder_level
    """
    p1_id = setup_reorder_data["p1_id"] # reorder_level = 10.0
    loc_id = setup_reorder_data["loc_id"] # available stock = 8.0

    # 1. Without rule: reorder_level is 10. Available (8) <= 10 -> Low stock.
    res1 = client.get(f"/api/inventory/low-stock?product_id={p1_id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert len(res1.json()) == 1

    # 2. Add product-wide rule minimum_quantity = 5.0. Available (8) > 5 -> NOT low stock.
    client.post(
        "/api/reorder-rules",
        json={"product_id": p1_id, "location_id": None, "minimum_quantity": 5, "reorder_quantity": 20},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    res2 = client.get(f"/api/inventory/low-stock?product_id={p1_id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert len(res2.json()) == 0

    # 3. Add location-specific rule minimum_quantity = 12.0. Available (8) <= 12 -> LOW stock again (location rule overrides product-wide rule).
    client.post(
        "/api/reorder-rules",
        json={"product_id": p1_id, "location_id": loc_id, "minimum_quantity": 12, "reorder_quantity": 20},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    res3 = client.get(f"/api/inventory/low-stock?product_id={p1_id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert len(res3.json()) == 1
    assert Decimal(str(res3.json()[0]["minimum_quantity"])) == Decimal("12")
