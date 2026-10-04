from unittest.mock import MagicMock, patch

import pytest
import requests

from app import openfoodfacts as off

SAMPLE = {
    "status": 1,
    "product": {
        "code": "3017620422003",
        "product_name": "Nutella",
        "brands": "Ferrero, Other",
        "categories": "Spreads, Sweet spreads",
        "quantity": "400 g",
        "ingredients_text": "Sugar",
        "image_front_url": "http://img/n.jpg",
    },
}


def fake_response(payload, ok=True):
    resp = MagicMock()
    resp.json.return_value = payload
    if ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = requests.HTTPError("500")
    return resp


@patch("app.openfoodfacts.requests.get")
def test_fetch_by_barcode_normalizes(mock_get):
    mock_get.return_value = fake_response(SAMPLE)
    p = off.fetch_by_barcode("3017620422003")
    assert p["name"] == "Nutella"
    assert p["brand"] == "Ferrero"
    assert p["category"] == "Spreads"
    assert "3017620422003" in mock_get.call_args[0][0]


@patch("app.openfoodfacts.requests.get")
def test_fetch_by_barcode_not_found(mock_get):
    mock_get.return_value = fake_response({"status": 0})
    with pytest.raises(off.ProductNotFound):
        off.fetch_by_barcode("123")


def test_fetch_by_barcode_rejects_non_numeric():
    with pytest.raises(ValueError):
        off.fetch_by_barcode("abc")


@patch("app.openfoodfacts.requests.get", side_effect=requests.Timeout)
def test_timeout_wrapped(_m):
    with pytest.raises(off.ExternalAPIError, match="timed out"):
        off.fetch_by_barcode("123")


@patch("app.openfoodfacts.requests.get", side_effect=requests.ConnectionError("boom"))
def test_connection_error_wrapped(_m):
    with pytest.raises(off.ExternalAPIError):
        off.fetch_by_barcode("123")


@patch("app.openfoodfacts.requests.get")
def test_http_error_wrapped(mock_get):
    mock_get.return_value = fake_response({}, ok=False)
    with pytest.raises(off.ExternalAPIError):
        off.fetch_by_barcode("123")


@patch("app.openfoodfacts.requests.get")
def test_invalid_json_wrapped(mock_get):
    resp = fake_response({})
    resp.json.side_effect = ValueError("bad")
    mock_get.return_value = resp
    with pytest.raises(off.ExternalAPIError, match="invalid JSON"):
        off.fetch_by_barcode("123")


@patch("app.openfoodfacts.requests.get")
def test_search_by_name(mock_get):
    mock_get.return_value = fake_response({"products": [SAMPLE["product"]] * 3})
    results = off.search_by_name("nutella", limit=2)
    assert len(results) == 2
    assert mock_get.call_args.kwargs["params"]["search_terms"] == "nutella"


@patch("app.openfoodfacts.requests.get")
def test_search_no_results(mock_get):
    mock_get.return_value = fake_response({"products": []})
    with pytest.raises(off.ProductNotFound):
        off.search_by_name("zzzz")


def test_search_empty_name():
    with pytest.raises(ValueError):
        off.search_by_name("  ")
