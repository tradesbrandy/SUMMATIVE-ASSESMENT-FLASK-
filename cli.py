
import argparse
import json
import os
import sys

import requests

DEFAULT_URL = os.environ.get("INVENTORY_API_URL", "http://127.0.0.1:5000")


class CLIError(Exception):
    pass


def api(method, base_url, path, **kwargs):
    try:
        resp = requests.request(method, f"{base_url}/api{path}", timeout=15, **kwargs)
    except requests.ConnectionError:
        raise CLIError(f"Cannot connect to API at {base_url}. Is the server running?")
    except requests.Timeout:
        raise CLIError("Request timed out")
    if resp.status_code == 204:
        return None
    try:
        data = resp.json()
    except ValueError:
        raise CLIError(f"Unexpected response ({resp.status_code})")
    if not resp.ok:
        raise CLIError(data.get("error", f"HTTP {resp.status_code}"))
    return data


def print_item(item):
    print(f"ID:          {item['id']}")
    print(f"Name:        {item['name']}")
    print(f"Barcode:     {item.get('barcode') or '-'}")
    print(f"Price:       {item['price']:.2f}")
    print(f"Quantity:    {item['quantity']}")
    print(f"Brand:       {item.get('brand') or '-'}")
    print(f"Category:    {item.get('category') or '-'}")
    if item.get("ingredients"):
        print(f"Ingredients: {item['ingredients'][:120]}")
    if item.get("image_url"):
        print(f"Image:       {item['image_url']}")


def print_table(items):
    if not items:
        print("No items found.")
        return
    print(f"{'ID':<5}{'NAME':<32}{'BARCODE':<16}{'PRICE':>8}{'QTY':>6}  BRAND")
    print("-" * 80)
    for i in items:
        print(
            f"{i['id']:<5}{i['name'][:30]:<32}{(i.get('barcode') or '-'):<16}"
            f"{i['price']:>8.2f}{i['quantity']:>6}  {i.get('brand') or ''}"
        )


def build_parser():
    p = argparse.ArgumentParser(description="Inventory admin CLI")
    p.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    p.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="Add a new item")
    a.add_argument("--name", required=True)
    a.add_argument("--barcode")
    a.add_argument("--price", type=float, default=0.0)
    a.add_argument("--quantity", type=int, default=0)
    a.add_argument("--brand")
    a.add_argument("--category")
    a.add_argument("--enrich", action="store_true",
                   help="Fetch extra details from OpenFoodFacts using the barcode")

    l = sub.add_parser("list", help="List items")
    l.add_argument("--search")
    l.add_argument("--category")

    v = sub.add_parser("view", help="View one item")
    v.add_argument("id", type=int)

    e = sub.add_parser("edit", help="Edit an item")
    e.add_argument("id", type=int)
    e.add_argument("--name")
    e.add_argument("--barcode")
    e.add_argument("--price", type=float)
    e.add_argument("--quantity", type=int)
    e.add_argument("--brand")
    e.add_argument("--category")

    d = sub.add_parser("delete", help="Delete an item")
    d.add_argument("id", type=int)
    d.add_argument("--yes", action="store_true", help="Skip confirmation")

    lb = sub.add_parser("lookup-barcode", help="Look up a product by barcode")
    lb.add_argument("barcode")

    ln = sub.add_parser("lookup-name", help="Search products by name")
    ln.add_argument("name")

    en = sub.add_parser("enrich", help="Fill blank details of an item from OpenFoodFacts")
    en.add_argument("id", type=int)
    return p


def run(args):
    url = args.url.rstrip("/")
    cmd = args.command

    if cmd == "add":
        body = {"name": args.name, "price": args.price, "quantity": args.quantity}
        for f in ("barcode", "brand", "category"):
            if getattr(args, f) is not None:
                body[f] = getattr(args, f)
        params = {"enrich": "1"} if args.enrich else None
        result = api("POST", url, "/items", json=body, params=params)
        print("Item created:")
        return result, print_item
    if cmd == "list":
        params = {k: v for k, v in (("search", args.search), ("category", args.category)) if v}
        return api("GET", url, "/items", params=params), print_table
    if cmd == "view":
        return api("GET", url, f"/items/{args.id}"), print_item
    if cmd == "edit":
        body = {f: getattr(args, f) for f in
                ("name", "barcode", "price", "quantity", "brand", "category")
                if getattr(args, f) is not None}
        if not body:
            raise CLIError("Nothing to update. Provide at least one field.")
        print("Item updated:")
        return api("PATCH", url, f"/items/{args.id}", json=body), print_item
    if cmd == "delete":
        if not args.yes:
            if input(f"Delete item {args.id}? [y/N] ").strip().lower() != "y":
                print("Cancelled.")
                return None, None
        api("DELETE", url, f"/items/{args.id}")
        print(f"Item {args.id} deleted.")
        return None, None
    if cmd == "lookup-barcode":
        return api("GET", url, f"/lookup/barcode/{args.barcode}"), print_lookup
    if cmd == "lookup-name":
        return api("GET", url, "/lookup/search", params={"name": args.name}), print_lookup_list
    if cmd == "enrich":
        print("Item enriched:")
        return api("POST", url, f"/items/{args.id}/enrich"), print_item
    raise CLIError(f"Unknown command {cmd}")


def print_lookup(p):
    print(f"Name:     {p['name'] or '-'}")
    print(f"Barcode:  {p['barcode']}")
    print(f"Brand:    {p['brand'] or '-'}")
    print(f"Category: {p['category'] or '-'}")
    print(f"Quantity: {p['quantity'] or '-'}")


def print_lookup_list(products):
    for n, p in enumerate(products, 1):
        print(f"{n}. {p['name'] or '(unnamed)'} | {p['brand'] or '-'} | barcode {p['barcode']}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        data, printer = run(args)
    except CLIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if data is None:
        return 0
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        printer(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
