# Inventory Admin Portal

A small inventory management system for an e-commerce retailer:

- **Flask REST API** with CRUD for inventory items (SQLite via SQLAlchemy)
- **OpenFoodFacts integration** to fetch product details by barcode or name
- **CLI** (`cli.py`) to drive the API from a terminal
- **Unit tests** (pytest) with the external API mocked

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run the API

```bash
python run.py          # http://127.0.0.1:5000
```

The SQLite database is created automatically (`instance/inventory.db`).



## Tests

```bash
python -m pytest -v
```

- `tests/test_api.py` – CRUD, validation, conflicts, enrichment endpoints
- `tests/test_openfoodfacts.py` – client parsing, not-found, timeout, HTTP and JSON errors
- `tests/test_cli.py` – CLI commands run end-to-end against the Flask test client

All external HTTP calls are mocked, so tests run offline.

## Layout

```
app/
  __init__.py        app factory
  models.py          Item model
  routes.py          REST endpoints + validation
  openfoodfacts.py   external API client
cli.py               command-line interface
run.py               dev server entry point
tests/
```
# SUMMATIVE-ASSESMENT-FLASK-
