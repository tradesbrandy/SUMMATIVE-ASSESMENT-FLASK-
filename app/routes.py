
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from . import openfoodfacts as off
from .models import Item, db

bp = Blueprint("inventory", __name__, url_prefix="/api")

STRING_FIELDS = ("name", "barcode", "brand", "category", "ingredients", "image_url")


def error(message, status):
    return jsonify({"error": message}), status


def validate(payload, partial=False):
    """Validate and clean a payload. Returns (clean, error_message)."""
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"
    clean = {}
    unknown = set(payload) - set(Item.FIELDS)
    if unknown:
        return None, f"Unknown fields: {', '.join(sorted(unknown))}"

    if not partial and not str(payload.get("name", "")).strip():
        return None, "'name' is required"

    for f in STRING_FIELDS:
        if f in payload:
            val = payload[f]
            if val is None and f == "barcode":
                clean[f] = None
                continue
            if not isinstance(val, str):
                return None, f"'{f}' must be a string"
            val = val.strip()
            if f == "name" and not val:
                return None, "'name' must not be empty"
            clean[f] = val or (None if f == "barcode" else "")

    if "price" in payload:
        try:
            price = float(payload["price"])
        except (TypeError, ValueError):
            return None, "'price' must be a number"
        if price < 0:
            return None, "'price' must be >= 0"
        clean["price"] = price

    if "quantity" in payload:
        q = payload["quantity"]
        if isinstance(q, bool) or not isinstance(q, int):
            return None, "'quantity' must be an integer"
        if q < 0:
            return None, "'quantity' must be >= 0"
        clean["quantity"] = q

    if clean.get("barcode") and not clean["barcode"].isdigit():
        return None, "'barcode' must be numeric"
    return clean, None


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@bp.get("/items")
def list_items():
    query = Item.query
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    if search:
        query = query.filter(Item.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(Item.category.ilike(f"%{category}%"))
    items = query.order_by(Item.id).all()
    return jsonify([i.to_dict() for i in items])


@bp.get("/items/<int:item_id>")
def get_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None:
        return error("Item not found", 404)
    return jsonify(item.to_dict())


@bp.post("/items")
def create_item():
    payload = request.get_json(silent=True)
    clean, err = validate(payload)
    if err:
        return error(err, 400)

    # Optionally enrich from OpenFoodFacts when asked and a barcode is given.
    enrich = request.args.get("enrich", "").lower() in ("1", "true", "yes")
    if enrich and clean.get("barcode"):
        try:
            external = off.fetch_by_barcode(clean["barcode"])
            for f in ("brand", "category", "ingredients", "image_url"):
                clean.setdefault(f, external.get(f, ""))
        except off.ProductNotFound:
            pass  # keep manual data
        except off.ExternalAPIError as exc:
            return error(str(exc), 502)

    item = Item(**clean)
    db.session.add(item)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("An item with this barcode already exists", 409)
    return jsonify(item.to_dict()), 201


@bp.put("/items/<int:item_id>")
@bp.patch("/items/<int:item_id>")
def update_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None:
        return error("Item not found", 404)
    payload = request.get_json(silent=True)
    clean, err = validate(payload, partial=True)
    if err:
        return error(err, 400)
    for key, val in clean.items():
        setattr(item, key, val)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("An item with this barcode already exists", 409)
    return jsonify(item.to_dict())


@bp.delete("/items/<int:item_id>")
def delete_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None:
        return error("Item not found", 404)
    db.session.delete(item)
    db.session.commit()
    return "", 204


@bp.get("/lookup/barcode/<barcode>")
def lookup_barcode(barcode):
    try:
        return jsonify(off.fetch_by_barcode(barcode))
    except ValueError as exc:
        return error(str(exc), 400)
    except off.ProductNotFound as exc:
        return error(str(exc), 404)
    except off.ExternalAPIError as exc:
        return error(str(exc), 502)


@bp.get("/lookup/search")
def lookup_search():
    name = request.args.get("name", "")
    try:
        return jsonify(off.search_by_name(name))
    except ValueError as exc:
        return error(str(exc), 400)
    except off.ProductNotFound as exc:
        return error(str(exc), 404)
    except off.ExternalAPIError as exc:
        return error(str(exc), 502)


@bp.post("/items/<int:item_id>/enrich")
def enrich_item(item_id):
    item = db.session.get(Item, item_id)
    if item is None:
        return error("Item not found", 404)
    if not item.barcode:
        return error("Item has no barcode to look up", 400)
    try:
        external = off.fetch_by_barcode(item.barcode)
    except off.ProductNotFound as exc:
        return error(str(exc), 404)
    except off.ExternalAPIError as exc:
        return error(str(exc), 502)
    for f in ("brand", "category", "ingredients", "image_url"):
        if not getattr(item, f) and external.get(f):
            setattr(item, f, external[f])
    db.session.commit()
    return jsonify(item.to_dict())
