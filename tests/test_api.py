from unittest.mock import patch

from app import openfoodfacts as off
from tests.conftest import OFF_PRODUCT


def make(client, **over):
    body = {"name": "Milk", "barcode": "111", "price": 1.5, "quantity": 10}
    body.update(over)
    return client.post("/api/items", json=body)


def test_root_lists_endpoints(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "endpoints" in r.get_json()




def test_create_and_get(client):
    r = make(client)
    assert r.status_code == 201
    item = r.get_json()
    assert item["name"] == "Milk" and item["quantity"] == 10
    r = client.get(f"/api/items/{item['id']}")
    assert r.status_code == 200 and r.get_json()["barcode"] == "111"


def test_list_search_and_category(client):
    make(client, name="Milk", barcode="1", category="Dairy")
    make(client, name="Bread", barcode="2", category="Bakery")
    assert len(client.get("/api/items").get_json()) == 2
    assert [i["name"] for i in client.get("/api/items?search=mil").get_json()] == ["Milk"]
    assert [i["name"] for i in client.get("/api/items?category=bake").get_json()] == ["Bread"]


def test_update_partial(client):
    item = make(client).get_json()
    r = client.patch(f"/api/items/{item['id']}", json={"price": 2.25, "quantity": 3})
    assert r.status_code == 200
    data = r.get_json()
    assert data["price"] == 2.25 and data["quantity"] == 3 and data["name"] == "Milk"


def test_delete(client):
    item = make(client).get_json()
    assert client.delete(f"/api/items/{item['id']}").status_code == 204
    assert client.get(f"/api/items/{item['id']}").status_code == 404


def test_not_found(client):
    assert client.get("/api/items/999").status_code == 404
    assert client.patch("/api/items/999", json={"price": 1}).status_code == 404
    assert client.delete("/api/items/999").status_code == 404


def test_duplicate_barcode_conflict(client):
    make(client)
    assert make(client, name="Other").status_code == 409




def test_validation_errors(client):
    assert client.post("/api/items", json={}).status_code == 400
    assert make(client, price=-1).status_code == 400
    assert make(client, price="abc").status_code == 400
    assert make(client, quantity=1.5).status_code == 400
    assert make(client, quantity=-2).status_code == 400
    assert make(client, barcode="12ab").status_code == 400
    assert make(client, bogus="x").status_code == 400
    assert client.post("/api/items", data="not json").status_code == 400


def test_update_rejects_empty_name(client):
    item = make(client).get_json()
    r = client.patch(f"/api/items/{item['id']}", json={"name": "  "})
    assert r.status_code == 400


# ---------- External API integration (mocked) ----------

@patch("app.routes.off.fetch_by_barcode", return_value=OFF_PRODUCT)
def test_lookup_barcode_endpoint(mock_fetch, client):
    r = client.get("/api/lookup/barcode/3017620422003")
    assert r.status_code == 200 and r.get_json()["brand"] == "Ferrero"
    mock_fetch.assert_called_once_with("3017620422003")


@patch("app.routes.off.fetch_by_barcode", side_effect=off.ProductNotFound("nope"))
def test_lookup_barcode_not_found(_m, client):
    assert client.get("/api/lookup/barcode/123").status_code == 404


@patch("app.routes.off.fetch_by_barcode", side_effect=off.ExternalAPIError("down"))
def test_lookup_barcode_upstream_failure(_m, client):
    assert client.get("/api/lookup/barcode/123").status_code == 502


def test_lookup_barcode_invalid(client):
    assert client.get("/api/lookup/barcode/abc").status_code == 400


@patch("app.routes.off.search_by_name", return_value=[OFF_PRODUCT])
def test_lookup_search(_m, client):
    r = client.get("/api/lookup/search?name=nutella")
    assert r.status_code == 200 and len(r.get_json()) == 1


def test_lookup_search_requires_name(client):
    assert client.get("/api/lookup/search").status_code == 400


@patch("app.routes.off.fetch_by_barcode", return_value=OFF_PRODUCT)
def test_create_with_enrich(_m, client):
    r = client.post("/api/items?enrich=1", json={"name": "Spread", "barcode": "3017620422003"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["brand"] == "Ferrero" and data["category"] == "Spreads"


@patch("app.routes.off.fetch_by_barcode", return_value=OFF_PRODUCT)
def test_create_enrich_keeps_manual_values(_m, client):
    r = client.post("/api/items?enrich=1",
                    json={"name": "Spread", "barcode": "3017620422003", "brand": "MyBrand"})
    assert r.get_json()["brand"] == "MyBrand"


@patch("app.routes.off.fetch_by_barcode", side_effect=off.ProductNotFound("x"))
def test_create_enrich_not_found_still_creates(_m, client):
    r = client.post("/api/items?enrich=1", json={"name": "Spread", "barcode": "999"})
    assert r.status_code == 201


@patch("app.routes.off.fetch_by_barcode", side_effect=off.ExternalAPIError("down"))
def test_create_enrich_upstream_failure(_m, client):
    r = client.post("/api/items?enrich=1", json={"name": "Spread", "barcode": "999"})
    assert r.status_code == 502


@patch("app.routes.off.fetch_by_barcode", return_value=OFF_PRODUCT)
def test_enrich_existing_item(_m, client):
    item = make(client, barcode="3017620422003").get_json()
    r = client.post(f"/api/items/{item['id']}/enrich")
    assert r.status_code == 200 and r.get_json()["brand"] == "Ferrero"


def test_enrich_item_without_barcode(client):
    item = client.post("/api/items", json={"name": "Loose"}).get_json()
    assert client.post(f"/api/items/{item['id']}/enrich").status_code == 400
