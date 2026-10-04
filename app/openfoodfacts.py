
import requests

BASE_URL = "https://world.openfoodfacts.org"
USER_AGENT = "InventoryAdminPortal/1.0 (inventory-admin@example.com)"
TIMEOUT = 8


class ExternalAPIError(Exception):
    pass


class ProductNotFound(ExternalAPIError):
    pass


def _normalize(product):
    
    return {
        "barcode": product.get("code") or product.get("_id"),
        "name": product.get("product_name") or product.get("generic_name") or "",
        "brand": (product.get("brands") or "").split(",")[0].strip(),
        "category": (product.get("categories") or "").split(",")[0].strip(),
        "quantity": product.get("quantity") or "",
        "ingredients": product.get("ingredients_text") or "",
        "image_url": product.get("image_front_url") or product.get("image_url") or "",
    }


def _get(url, params=None):
    try:
        resp = requests.get(
            url, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}
        )
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout as exc:
        raise ExternalAPIError("External API timed out") from exc
    except requests.RequestException as exc:
        raise ExternalAPIError(f"External API request failed: {exc}") from exc
    except ValueError as exc:
        raise ExternalAPIError("External API returned invalid JSON") from exc


def fetch_by_barcode(barcode):
    
    barcode = str(barcode).strip()
    if not barcode.isdigit():
        raise ValueError("Barcode must be numeric")
    data = _get(f"{BASE_URL}/api/v2/product/{barcode}.json")
    if data.get("status") != 1 or "product" not in data:
        raise ProductNotFound(f"No product found for barcode {barcode}")
    result = _normalize(data["product"])
    result["barcode"] = result["barcode"] or barcode
    return result


def search_by_name(name, limit=5):
    
    name = (name or "").strip()
    if not name:
        raise ValueError("Name must not be empty")
    data = _get(
        f"{BASE_URL}/cgi/search.pl",
        params={
            "search_terms": name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": limit,
        },
    )
    products = data.get("products") or []
    if not products:
        raise ProductNotFound(f"No products found for '{name}'")
    return [_normalize(p) for p in products[:limit]]
