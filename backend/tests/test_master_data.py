from decimal import Decimal
import pytest
from app.models import Category, Inventory, Location, Product, Warehouse


@pytest.fixture
def manager_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Manager One",
            "email": "mgr1@example.com",
            "password": "Password123!",
            "role": "INVENTORY_MANAGER",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "mgr1@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def staff_token(client):
    client.post(
        "/api/auth/signup",
        json={
            "name": "Staff One",
            "email": "staff1@example.com",
            "password": "Password123!",
            "role": "WAREHOUSE_STAFF",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "staff1@example.com", "password": "Password123!"},
    )
    return resp.json()["access_token"]


# ==========================================
# CATEGORY TESTS
# ==========================================

def test_manager_creates_category(client, manager_token):
    resp = client.post(
        "/api/categories",
        json={"name": "Raw Materials", "description": "Metals and polymers"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Raw Materials"
    assert data["is_active"] is True


def test_staff_cannot_create_category(client, staff_token):
    resp = client.post(
        "/api/categories",
        json={"name": "Forbidden Cat"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403


def test_duplicate_category_rejected(client, manager_token):
    client.post(
        "/api/categories",
        json={"name": "Electronics"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    resp = client.post(
        "/api/categories",
        json={"name": "electronics"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 409


def test_category_list_read_update_delete(client, manager_token, staff_token):
    cat_id = client.post(
        "/api/categories",
        json={"name": "Tools", "description": "Hand tools"},
        headers={"Authorization": f"Bearer {manager_token}"},
    ).json()["id"]

    # Staff can read
    list_resp = client.get(
        "/api/categories?search=tool",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Read single
    get_resp = client.get(
        f"/api/categories/{cat_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert get_resp.status_code == 200

    # Manager update
    patch_resp = client.patch(
        f"/api/categories/{cat_id}",
        json={"description": "Power and hand tools"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["description"] == "Power and hand tools"

    # Manager deactivate
    del_resp = client.delete(
        f"/api/categories/{cat_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert del_resp.status_code == 200

    get_after = client.get(
        f"/api/categories/{cat_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert get_after.json()["is_active"] is False


# ==========================================
# WAREHOUSE TESTS
# ==========================================

def test_warehouse_crud(client, manager_token, staff_token):
    # Manager create
    resp = client.post(
        "/api/warehouses",
        json={"name": "Central Hub", "code": " wh-01 ", "address": "123 Main St"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "WH-01"
    wh_id = data["id"]

    # Duplicate code rejected
    dup_resp = client.post(
        "/api/warehouses",
        json={"name": "Other Hub", "code": "WH-01"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert dup_resp.status_code == 409

    # Update
    update_resp = client.patch(
        f"/api/warehouses/{wh_id}",
        json={"name": "Central Logistics Hub"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Central Logistics Hub"

    # Deactivate
    del_resp = client.delete(
        f"/api/warehouses/{wh_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert del_resp.status_code == 200


def test_staff_cannot_create_update_delete_warehouse(client, manager_token, staff_token):
    wh_id = client.post(
        "/api/warehouses",
        json={"name": "WH Staff Test", "code": "WH-ST"},
        headers={"Authorization": f"Bearer {manager_token}"},
    ).json()["id"]

    # Staff POST -> 403
    post_resp = client.post(
        "/api/warehouses",
        json={"name": "Staff WH", "code": "WH-ST2"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert post_resp.status_code == 403

    # Staff PATCH -> 403
    patch_resp = client.patch(
        f"/api/warehouses/{wh_id}",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert patch_resp.status_code == 403

    # Staff DELETE -> 403
    del_resp = client.delete(
        f"/api/warehouses/{wh_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert del_resp.status_code == 403


# ==========================================
# LOCATION TESTS
# ==========================================

def test_location_crud(client, manager_token, staff_token):
    wh_id = client.post(
        "/api/warehouses",
        json={"name": "North Storage", "code": "WH-NORTH"},
        headers={"Authorization": f"Bearer {manager_token}"},
    ).json()["id"]

    # Invalid warehouse rejected
    bad_wh = client.post(
        "/api/locations",
        json={"warehouse_id": 99999, "name": "Shelf 1", "code": "LOC-BAD"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert bad_wh.status_code == 404

    # Manager creates location
    loc_resp = client.post(
        "/api/locations",
        json={"warehouse_id": wh_id, "name": "Aisle 1", "code": " loc-a1 "},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert loc_resp.status_code == 201
    loc_data = loc_resp.json()
    assert loc_data["code"] == "LOC-A1"
    loc_id = loc_data["id"]

    # Duplicate code rejected
    dup_loc = client.post(
        "/api/locations",
        json={"warehouse_id": wh_id, "name": "Aisle 2", "code": "LOC-A1"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert dup_loc.status_code == 409

    # Staff filter by warehouse
    list_resp = client.get(
        f"/api/locations?warehouse_id={wh_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Deactivate location
    del_resp = client.delete(
        f"/api/locations/{loc_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert del_resp.status_code == 200


def test_staff_cannot_create_update_delete_location(client, manager_token, staff_token):
    wh_id = client.post(
        "/api/warehouses",
        json={"name": "WH Loc Test", "code": "WH-LT"},
        headers={"Authorization": f"Bearer {manager_token}"},
    ).json()["id"]

    loc_id = client.post(
        "/api/locations",
        json={"warehouse_id": wh_id, "name": "Loc Staff Test", "code": "LOC-ST"},
        headers={"Authorization": f"Bearer {manager_token}"},
    ).json()["id"]

    # Staff POST -> 403
    post_resp = client.post(
        "/api/locations",
        json={"warehouse_id": wh_id, "name": "Staff Loc", "code": "LOC-ST2"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert post_resp.status_code == 403

    # Staff PATCH -> 403
    patch_resp = client.patch(
        f"/api/locations/{loc_id}",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert patch_resp.status_code == 403

    # Staff DELETE -> 403
    del_resp = client.delete(
        f"/api/locations/{loc_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert del_resp.status_code == 403


# ==========================================
# PRODUCT TESTS
# ==========================================

def test_product_crud_and_filters(client, manager_token, staff_token):
    cat_id = client.post(
        "/api/categories",
        json={"name": "Components"},
        headers={"Authorization": f"Bearer {manager_token}"},
    ).json()["id"]

    # Invalid category rejected
    bad_cat = client.post(
        "/api/products",
        json={"name": "Widget", "sku": "SKU-W1", "category_id": 99999},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert bad_cat.status_code == 404

    # Manager creates product
    p1 = client.post(
        "/api/products",
        json={
            "name": "Steel Bolt",
            "sku": " sku-bolt-01 ",
            "category_id": cat_id,
            "unit_of_measure": "pcs",
            "reorder_level": "10.0000",
            "reorder_quantity": "50.0000",
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert p1.status_code == 201
    p1_data = p1.json()
    assert p1_data["sku"] == "SKU-BOLT-01"
    prod_id = p1_data["id"]

    # Duplicate SKU rejected
    dup_sku = client.post(
        "/api/products",
        json={"name": "Iron Bolt", "sku": "SKU-BOLT-01"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert dup_sku.status_code == 409

    # Staff search by SKU and category filter
    filter_resp = client.get(
        f"/api/products?sku=SKU-BOLT-01&category_id={cat_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert filter_resp.status_code == 200
    assert len(filter_resp.json()) == 1

    # Search by name
    search_resp = client.get(
        "/api/products?search=bolt",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert search_resp.status_code == 200
    assert len(search_resp.json()) == 1

    # Deactivate product
    del_resp = client.delete(
        f"/api/products/{prod_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert del_resp.status_code == 200


def test_staff_cannot_create_update_delete_product(client, manager_token, staff_token):
    prod_id = client.post(
        "/api/products",
        json={"name": "Prod Staff Test", "sku": "SKU-PROD-ST"},
        headers={"Authorization": f"Bearer {manager_token}"},
    ).json()["id"]

    # Staff POST -> 403
    post_resp = client.post(
        "/api/products",
        json={"name": "Staff Prod", "sku": "SKU-PROD-ST2"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert post_resp.status_code == 403

    # Staff PATCH -> 403
    patch_resp = client.patch(
        f"/api/products/{prod_id}",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert patch_resp.status_code == 403

    # Staff DELETE -> 403
    del_resp = client.delete(
        f"/api/products/{prod_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert del_resp.status_code == 403


# ==========================================
# UNAUTHENTICATED ACCESS TESTS
# ==========================================

def test_unauthenticated_requests_rejected(client):
    assert client.get("/api/categories").status_code == 401
    assert client.get("/api/products").status_code == 401
    assert client.get("/api/warehouses").status_code == 401
    assert client.get("/api/locations").status_code == 401
    assert client.get("/api/inventory").status_code == 401
    assert client.get("/api/products/1/stock").status_code == 401


# ==========================================
# READ-ONLY STOCK & INVENTORY TESTS
# ==========================================

def test_stock_aggregation_and_inventory_queries(client, manager_token, staff_token, db_session):
    # Create category, product, warehouse, locations
    cat = Category(name="Raw Stock")
    db_session.add(cat)
    db_session.commit()

    prod = Product(
        name="Aluminum Sheet",
        sku="ALU-001",
        category_id=cat.id,
        reorder_level=Decimal("20.0000"),
    )
    wh1 = Warehouse(name="East Hub", code="WH-E")
    wh2 = Warehouse(name="West Hub", code="WH-W")
    db_session.add_all([prod, wh1, wh2])
    db_session.commit()

    loc1 = Location(warehouse_id=wh1.id, name="Rack 1", code="LOC-R1")
    loc2 = Location(warehouse_id=wh2.id, name="Rack 2", code="LOC-R2")
    db_session.add_all([loc1, loc2])
    db_session.commit()

    # Add inventory records directly in test setup
    inv1 = Inventory(
        product_id=prod.id,
        location_id=loc1.id,
        quantity=Decimal("100.0000"),
        reserved_quantity=Decimal("10.0000"),
    )
    inv2 = Inventory(
        product_id=prod.id,
        location_id=loc2.id,
        quantity=Decimal("50.0000"),
        reserved_quantity=Decimal("5.0000"),
    )
    db_session.add_all([inv1, inv2])
    db_session.commit()

    # Test GET /api/products/{product_id}/stock
    stock_resp = client.get(
        f"/api/products/{prod.id}/stock",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert stock_resp.status_code == 200
    stock_data = stock_resp.json()
    assert stock_data["product_id"] == prod.id
    assert stock_data["sku"] == "ALU-001"
    assert Decimal(str(stock_data["total_quantity"])) == Decimal("150.0000")
    assert Decimal(str(stock_data["total_reserved_quantity"])) == Decimal("15.0000")
    assert Decimal(str(stock_data["total_available_quantity"])) == Decimal("135.0000")
    assert len(stock_data["locations"]) == 2

    # Verify per-location math
    loc_detail_1 = next(l for l in stock_data["locations"] if l["location_id"] == loc1.id)
    assert Decimal(str(loc_detail_1["available_quantity"])) == Decimal("90.0000")

    # Test GET /api/inventory with warehouse_id filter
    inv_wh_resp = client.get(
        f"/api/inventory?warehouse_id={wh1.id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert inv_wh_resp.status_code == 200
    assert len(inv_wh_resp.json()) == 1
    assert inv_wh_resp.json()[0]["location_id"] == loc1.id

    # Test GET /api/inventory with category_id filter
    inv_cat_resp = client.get(
        f"/api/inventory?category_id={cat.id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert inv_cat_resp.status_code == 200
    assert len(inv_cat_resp.json()) == 2

    # Test GET /api/inventory/{product_id}/locations
    prod_locs_resp = client.get(
        f"/api/inventory/{prod.id}/locations",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert prod_locs_resp.status_code == 200
    assert len(prod_locs_resp.json()) == 2


def test_explicit_inventory_filters_and_stock_conditions(client, staff_token, db_session):
    cat1 = Category(name="Cat Filter 1")
    cat2 = Category(name="Cat Filter 2")
    db_session.add_all([cat1, cat2])
    db_session.commit()

    p_normal = Product(name="Normal Stock Prod", sku="SKU-NORM", category_id=cat1.id, reorder_level=Decimal("10.0000"))
    p_low = Product(name="Low Stock Prod", sku="SKU-LOW", category_id=cat1.id, reorder_level=Decimal("20.0000"))
    p_out = Product(name="Out Stock Prod", sku="SKU-OUT", category_id=cat2.id, reorder_level=Decimal("5.0000"))
    wh = Warehouse(name="Filter WH", code="WH-FLT")
    db_session.add_all([p_normal, p_low, p_out, wh])
    db_session.commit()

    l1 = Location(warehouse_id=wh.id, name="Loc 1", code="LOC-F1")
    l2 = Location(warehouse_id=wh.id, name="Loc 2", code="LOC-F2")
    db_session.add_all([l1, l2])
    db_session.commit()

    inv_normal = Inventory(product_id=p_normal.id, location_id=l1.id, quantity=Decimal("100.0000"), reserved_quantity=Decimal("0.0000"))
    inv_low = Inventory(product_id=p_low.id, location_id=l1.id, quantity=Decimal("15.0000"), reserved_quantity=Decimal("0.0000"))
    inv_out = Inventory(product_id=p_out.id, location_id=l2.id, quantity=Decimal("5.0000"), reserved_quantity=Decimal("5.0000"))
    db_session.add_all([inv_normal, inv_low, inv_out])
    db_session.commit()

    # Filter by product_id
    res_prod = client.get(f"/api/inventory?product_id={p_normal.id}", headers={"Authorization": f"Bearer {staff_token}"}).json()
    assert len(res_prod) == 1
    assert res_prod[0]["sku"] == "SKU-NORM"

    # Filter by location_id
    res_loc = client.get(f"/api/inventory?location_id={l2.id}", headers={"Authorization": f"Bearer {staff_token}"}).json()
    assert len(res_loc) == 1
    assert res_loc[0]["sku"] == "SKU-OUT"

    # Filter by category_id
    res_cat = client.get(f"/api/inventory?category_id={cat1.id}", headers={"Authorization": f"Bearer {staff_token}"}).json()
    assert len(res_cat) == 2

    # Filter by low_stock=true (available <= reorder_level: includes p_low & p_out)
    res_low = client.get("/api/inventory?low_stock=true", headers={"Authorization": f"Bearer {staff_token}"}).json()
    skus_low = [item["sku"] for item in res_low]
    assert "SKU-LOW" in skus_low
    assert "SKU-OUT" in skus_low
    assert "SKU-NORM" not in skus_low

    # Filter by out_of_stock=true (available <= 0: includes p_out only)
    res_out = client.get("/api/inventory?out_of_stock=true", headers={"Authorization": f"Bearer {staff_token}"}).json()
    assert len(res_out) == 1
    assert res_out[0]["sku"] == "SKU-OUT"


def test_soft_delete_preserves_db_records(client, manager_token, db_session):
    # Create category, warehouse, location, product
    cat_id = client.post("/api/categories", json={"name": "Preserve Cat"}, headers={"Authorization": f"Bearer {manager_token}"}).json()["id"]
    wh_id = client.post("/api/warehouses", json={"name": "Preserve WH", "code": "WH-PRS"}, headers={"Authorization": f"Bearer {manager_token}"}).json()["id"]
    loc_id = client.post("/api/locations", json={"warehouse_id": wh_id, "name": "Preserve Loc", "code": "LOC-PRS"}, headers={"Authorization": f"Bearer {manager_token}"}).json()["id"]
    prod_id = client.post("/api/products", json={"name": "Preserve Prod", "sku": "SKU-PRS"}, headers={"Authorization": f"Bearer {manager_token}"}).json()["id"]

    # Call DELETE on all four
    client.delete(f"/api/categories/{cat_id}", headers={"Authorization": f"Bearer {manager_token}"})
    client.delete(f"/api/warehouses/{wh_id}", headers={"Authorization": f"Bearer {manager_token}"})
    client.delete(f"/api/locations/{loc_id}", headers={"Authorization": f"Bearer {manager_token}"})
    client.delete(f"/api/products/{prod_id}", headers={"Authorization": f"Bearer {manager_token}"})

    # Verify directly in DB that records exist and is_active is False
    cat_db = db_session.query(Category).filter(Category.id == cat_id).first()
    wh_db = db_session.query(Warehouse).filter(Warehouse.id == wh_id).first()
    loc_db = db_session.query(Location).filter(Location.id == loc_id).first()
    prod_db = db_session.query(Product).filter(Product.id == prod_id).first()

    assert cat_db is not None and cat_db.is_active is False
    assert wh_db is not None and wh_db.is_active is False
    assert loc_db is not None and loc_db.is_active is False
    assert prod_db is not None and prod_db.is_active is False
