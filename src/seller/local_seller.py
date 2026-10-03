#!/usr/bin/env python3
"""Loopback-only catalog editor and safe CSV persistence service."""

import csv
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "catalog_data.xlsx"
HISTORY_FILE = ROOT / "data" / ".seller_history.json"
HOST = "127.0.0.1"
PORT = 8766
MAX_HISTORY = 50

sys.path.insert(0, str(ROOT))
from src import build_catalog
from src.seller import prepare_tally_files



CLIENT_FILE = ROOT / "data" / "client_data.xlsx"

def read_clients():
    if not CLIENT_FILE.exists():
        return []
    if CLIENT_FILE.suffix == ".csv":
        with CLIENT_FILE.open(encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))
    import openpyxl
    wb = openpyxl.load_workbook(CLIENT_FILE, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        return []
    fields = [str(c).strip() for c in all_rows[0] if c is not None]
    clients = []
    for r in all_rows[1:]:
        if not any(v is not None and str(v).strip() for v in r):
            continue
        client = {
            fields[i]: str(r[i]).strip() if i < len(r) and r[i] is not None else ""
            for i in range(len(fields))
        }
        clients.append(client)
    return clients

def append_client(new_client):
    clients = read_clients()
    gstin = str(new_client.get('gstin', '') or '').strip()
    name = str(new_client.get('name', '') or '').strip()
    
    updated_existing = False
    for c in clients:
        if (gstin and c.get('gstin') == gstin) or (name and c.get('name', '').lower() == name.lower()):
            updated_existing = True
            for k in ['phone', 'email', 'address', 'state', 'pincode', 'gstin']:
                if new_client.get(k):
                    c[k] = str(new_client.get(k))
            break
            
    fieldnames = ['client_id','name','business_name','phone','email','address','state','pincode','gstin']
    
    if not updated_existing:
        if not new_client.get('client_id'):
            new_client['client_id'] = gstin if gstin else name.upper().replace(' ', '_')[:10]
        clean_new = {k: str(new_client.get(k, '') or '') for k in fieldnames}
        clients.append(clean_new)

    if CLIENT_FILE.suffix == ".csv":
        with CLIENT_FILE.open(mode='w', encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for c in clients:
                writer.writerow({k: c.get(k, '') for k in fieldnames})
        return True

    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clients"
    for c_idx, field in enumerate(fieldnames, 1):
        cell = ws.cell(row=1, column=c_idx, value=field)
        cell.data_type = 's'
        cell.number_format = '@'
    for r_idx, c in enumerate(clients, 2):
        for c_idx, field in enumerate(fieldnames, 1):
            val = str(c.get(field, '') or '').strip()
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.data_type = 's'
            cell.number_format = '@'

    temp_xlsx = CLIENT_FILE.parent / f".client_data-{os.getpid()}.tmp.xlsx"
    try:
        wb.save(temp_xlsx)
        os.replace(temp_xlsx, CLIENT_FILE)
    finally:
        if temp_xlsx.exists():
            temp_xlsx.unlink()
            
    return True


BILLS_DIR = ROOT / "data" / "bills"
ESTIMATES_DIR = ROOT / "data" / "estimates"
GENERATED_BILLS_DIR = ROOT / "data" / "generated_bills"


def _pick(mapping, *keys, default=""):
    """Return the first non-empty value among `keys`."""
    if not isinstance(mapping, dict):
        return default
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return default


def append_bill(order):
    BILLS_DIR.mkdir(parents=True, exist_ok=True)
    ESTIMATES_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_BILLS_DIR.mkdir(parents=True, exist_ok=True)
    created_at = _pick(order, 'createdAt', 'created_at')
    if not created_at:
        return None
        
    month = str(created_at)[:7]  # YYYY-MM
    is_estimate = order.get("isEstimate", False)
    target_dir = ESTIMATES_DIR if is_estimate else BILLS_DIR
    xlsx_file = target_dir / f"{month}.xlsx"
    csv_file = target_dir / f"{month}.csv"
    
    fieldnames = ['id', 'createdAt', 'org', 'buyer_name', 'buyer_phone', 'subTotal', 'grandTotal', 'order_json']

    org = order.get("org", "skumar")
    org_prefix = {"skumar": "S", "gsc": "G"}.get(org, "S")
    prefix = "EST" if is_estimate else org_prefix

    existing_rows = []
    if xlsx_file.exists():
        import openpyxl
        wb = openpyxl.load_workbook(xlsx_file, data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        if all_rows:
            f_names = [str(c).strip() for c in all_rows[0] if c is not None]
            for r in all_rows[1:]:
                if any(v is not None and str(v).strip() for v in r):
                    existing_rows.append({
                        f_names[i]: str(r[i]).strip() if i < len(r) and r[i] is not None else ""
                        for i in range(len(f_names))
                    })
    elif csv_file.exists():
        with csv_file.open(encoding="utf-8-sig", newline="") as f:
            existing_rows = list(csv.DictReader(f))

    assigned_id = _pick(order, 'id', 'order_reference')
    if (not assigned_id or len(assigned_id) > 15 or 'PI-' in assigned_id
            or not assigned_id.startswith(prefix + "-")):
        assigned_id = f"{prefix}-{month.replace('-', '')}-{len(existing_rows) + 1:04d}"
        order['id'] = assigned_id

    buyer = _pick(order, 'buyer', 'customer', default={}) or {}
    totals = _pick(order, 'totals', default={}) or {}
    amounts = _pick(order, 'amounts', default={}) or {}

    row = {
        'id': assigned_id,
        'createdAt': created_at,
        'org': org,
        'buyer_name': _pick(buyer, 'name') or '',
        'buyer_phone': _pick(buyer, 'phone') or '',
        'subTotal': totals.get('subTotal', amounts.get('taxable_subtotal', 0)),
        'grandTotal': totals.get('grandTotal', amounts.get('estimated_total', 0)),
        'order_json': json.dumps(order)
    }
    
    # Update if exists, else append
    found = False
    for i, existing_row in enumerate(existing_rows):
        if existing_row.get('id') == row['id']:
            existing_rows[i] = row
            found = True
            break
    if not found:
        existing_rows.append(row)

    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = month[:31]
    for c_idx, field in enumerate(fieldnames, 1):
        cell = ws.cell(row=1, column=c_idx, value=field)
        cell.data_type = 's'
        cell.number_format = '@'
    for r_idx, r_data in enumerate(existing_rows, 2):
        for c_idx, field in enumerate(fieldnames, 1):
            val = str(r_data.get(field, '') or '').strip()
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.data_type = 's'
            cell.number_format = '@'
    
    temp_xlsx = target_dir / f".{month}-{os.getpid()}.tmp.xlsx"
    try:
        wb.save(temp_xlsx)
        os.replace(temp_xlsx, xlsx_file)
    finally:
        if temp_xlsx.exists():
            temp_xlsx.unlink()

    # Always ensure standalone HTML is archived in data/generated_bills/{month}/{assigned_id}.html
    generated_month_dir = GENERATED_BILLS_DIR / month
    generated_month_dir.mkdir(parents=True, exist_ok=True)
    html_file = generated_month_dir / f"{assigned_id}.html"
    
    html_payload = order.get('html')
    if not html_payload:
        b_name = row['buyer_name'] or 'Customer'
        b_phone = row['buyer_phone'] or ''
        items_list = order.get('items', [])
        items_rows = "".join(f"<tr><td>{it.get('sr_number','')}</td><td>{it.get('item_name','')}</td><td>{it.get('qty','1')}</td><td>{it.get('price','')}</td></tr>" for it in items_list)
        html_payload = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Bill {assigned_id}</title></head>
<body>
<h1>Proforma Invoice: {assigned_id}</h1>
<p>Date: {created_at} | Customer: {b_name} | Phone: {b_phone}</p>
<table border="1" cellpadding="6" cellspacing="0">
<thead><tr><th>Sr.</th><th>Item</th><th>Qty</th><th>Price</th></tr></thead>
<tbody>{items_rows}</tbody>
</table>
<p>Subtotal: ₹{row['subTotal']} | Grand Total: ₹{row['grandTotal']}</p>
</body>
</html>"""
    html_file.write_text(html_payload, encoding="utf-8")
    
    return row

def read_bills():
    BILLS_DIR.mkdir(parents=True, exist_ok=True)
    ESTIMATES_DIR.mkdir(parents=True, exist_ok=True)
    bills = []
    import re as regex
    for target_dir in [BILLS_DIR, ESTIMATES_DIR]:
        # Support both .xlsx and .csv files
        files = sorted(target_dir.glob("*.xlsx")) + sorted(target_dir.glob("*.csv"))
        seen_months = set()
        for b_file in files:
            m_match = regex.match(r"^(\d{4}-\d{2})\.(xlsx|csv)$", b_file.name)
            if not m_match:
                continue
            month = m_match.group(1)
            # Prefer xlsx over csv if both exist for a month
            if month in seen_months and b_file.suffix == ".csv":
                continue
            seen_months.add(month)
            
            rows = []
            if b_file.suffix == ".xlsx":
                import openpyxl
                wb = openpyxl.load_workbook(b_file, data_only=True)
                ws = wb.active
                all_rows = list(ws.iter_rows(values_only=True))
                if all_rows:
                    f_names = [str(c).strip() for c in all_rows[0] if c is not None]
                    for r in all_rows[1:]:
                        if any(v is not None and str(v).strip() for v in r):
                            rows.append({
                                f_names[i]: str(r[i]).strip() if i < len(r) and r[i] is not None else ""
                                for i in range(len(f_names))
                            })
            else:
                with b_file.open(encoding="utf-8-sig", newline="") as f:
                    rows = list(csv.DictReader(f))

            for row in rows:
                bills.append({
                    "id": row.get('id'),
                    "month": month,
                    "createdAt": row.get('createdAt'),
                    "reference": f"{row.get('id')} - {row.get('buyer_name')}",
                    "buyer_name": row.get('buyer_name'),
                    "grandTotal": row.get('grandTotal'),
                    "storage": "server",
                    "order_json": row.get('order_json'),
                    "isEstimate": target_dir == ESTIMATES_DIR
                })
    return sorted(bills, key=lambda x: x.get('createdAt', ''), reverse=True)


def read_catalog():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Catalog file not found: {DATA_FILE}")

    raw = DATA_FILE.read_bytes()
    if DATA_FILE.suffix == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(DATA_FILE, data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            return [], [], hashlib.sha256(raw).hexdigest()
        fields = [str(col).strip() for col in all_rows[0] if col is not None]
        rows = []
        for r in all_rows[1:]:
            if not any(v is not None and str(v).strip() for v in r):
                continue
            item = {}
            for col_idx, key in enumerate(fields):
                val = r[col_idx] if col_idx < len(r) else ''
                if val is None:
                    item[key] = ''
                elif key == 'sr_number':
                    item[key] = str(val).strip()
                elif isinstance(val, float) and val.is_integer() and key in ('hsn_code', 'page'):
                    item[key] = str(int(val))
                else:
                    item[key] = str(val).strip()
            rows.append(item)
    else:
        with DATA_FILE.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            fields = list(reader.fieldnames or [])
            rows = list(reader)

    if "hidden" not in fields:
        fields.append("hidden")
        for row in rows:
            row["hidden"] = ""
    return fields, rows, hashlib.sha256(raw).hexdigest()


def write_catalog(fields, rows):
    fields = list(fields)
    if "hidden" not in fields:
        fields.append("hidden")

    if DATA_FILE.suffix == ".xlsx":
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Catalog"
        for c_idx, field in enumerate(fields, 1):
            cell = ws.cell(row=1, column=c_idx, value=field)
            cell.data_type = 's'
            cell.number_format = '@'
        for r_idx, row in enumerate(rows, 2):
            for c_idx, field in enumerate(fields, 1):
                val = str(row.get(field, "") or "").strip()
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.data_type = 's'
                cell.number_format = '@'

        temp_xlsx = DATA_FILE.parent / f".catalog_data-{os.getpid()}.tmp.xlsx"
        try:
            wb.save(temp_xlsx)
            os.replace(temp_xlsx, DATA_FILE)
        finally:
            if temp_xlsx.exists():
                temp_xlsx.unlink()
    else:
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8-sig",
                newline="",
                dir=DATA_FILE.parent,
                prefix=".catalog_data-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                writer = csv.DictWriter(temporary, fieldnames=fields, extrasaction="raise")
                writer.writeheader()
                writer.writerows(rows)
            os.replace(temporary_path, DATA_FILE)
            temporary_path = None
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    # Automatically synchronize image_serial_map directly from catalog items if updating canonical catalog
    try:
        if DATA_FILE.resolve() == (ROOT / "data" / "catalog_data.xlsx").resolve():
            build_catalog.sync_image_serial_map(rows)
    except Exception:
        pass


def read_history():
    if not HISTORY_FILE.exists():
        return []
    history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    if not isinstance(history, list):
        raise ValueError("Seller undo history has an invalid format.")
    return history[-MAX_HISTORY:]


def write_history(history):
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=HISTORY_FILE.parent,
            prefix=".seller_history-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(history[-MAX_HISTORY:], temporary, ensure_ascii=False)
            temporary.write("\n")
        os.replace(temporary_path, HISTORY_FILE)
        temporary_path = None
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def validate_rows(fields, rows):
    if not rows:
        raise ValueError("The catalog must contain at least one product.")
    if len(fields) != len(set(fields)):
        raise ValueError("Catalog field names must be unique.")
    allowed_fields = set(fields)
    cleaned = []
    for row in rows:
        # We allow extra frontend-only fields (like display_image_path) to be present,
        # but we only save the fields that belong in the catalog.
        item = {field: "" if row.get(field) is None else str(row.get(field)).strip() for field in fields}
        if item.get("hidden", "").lower() not in {"", "0", "1", "true", "false", "yes", "no"}:
            raise ValueError(f"Invalid hidden flag for sr_number {item.get('sr_number', '')}.")
        item["hidden"] = "true" if item["hidden"].lower() in {"1", "true", "yes"} else ""
        cleaned.append(item)

    build_catalog.validate_catalog_data(cleaned)
    return cleaned


def update_catalog(rows, expected_revision):
    fields, current_rows, current_revision = read_catalog()
    if expected_revision != current_revision:
        raise ValueError("The catalog changed in another window. Reload before saving.")
    cleaned = validate_rows(fields, rows)
    history = read_history()
    history.append({
        "fields": fields,
        "rows": current_rows,
        "revision": current_revision,
    })
    write_catalog(fields, cleaned)
    write_history(history)
    new_fields, new_rows, new_revision = read_catalog()
    return new_fields, new_rows, new_revision


def undo_catalog(expected_revision):
    fields, _, current_revision = read_catalog()
    if expected_revision != current_revision:
        raise ValueError("The catalog changed in another window. Reload before undoing.")
    history = read_history()
    if not history:
        raise ValueError("There are no saved changes to undo.")
    snapshot = history.pop()
    restored = validate_rows(snapshot["fields"], snapshot["rows"])
    write_catalog(snapshot["fields"], restored)
    write_history(history)
    new_fields, new_rows, new_revision = read_catalog()
    return new_fields, new_rows, new_revision


def run_updater():
    """Rebuild the pages and run the full suite after a catalog save.

    Cross-platform: update.sh is the documented entry point, but the seller
    server must not depend on a shell script that Windows cannot run.
    """
    subprocess.run(
        [sys.executable, str(ROOT / "src" / "build_catalog.py")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        cwd=ROOT,
        check=True,
    )
    for test_file in ("order_core.test.js", "client_directory.test.js", "bill_archive.test.js"):
        subprocess.run(["node", f"tests/{test_file}"], cwd=ROOT, check=True)


class SellerHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format_string, *args):
        print(f"[seller] {self.address_string()} {format_string % args}")

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.end_headers()

    def authorized_local_request(self):
        host = self.headers.get("Host", "")
        allowed_hosts = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        if host not in allowed_hosts:
            return False
        origin = self.headers.get("Origin")
        if origin and origin != "null" and origin not in {
            f"http://127.0.0.1:{PORT}",
            f"http://localhost:{PORT}",
        }:
            return False
        return True

    def do_GET(self):
        if not self.authorized_local_request():
            self.send_error(403, "Seller tools are available only over the local loopback server.")
            return
            
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
            return

        if self.path == "/api/bills":
            self.send_json(200, {"bills": read_bills()})
            return
            
        if self.path == "/api/clients":
            self.send_json(200, {"clients": read_clients()})
            return
        if self.path == "/api/catalog":
            fields, rows, revision = read_catalog()
            # Augment rows with image paths using build_catalog logic
            active_items = build_catalog.visible_catalog_items(rows)
            categories = build_catalog.group_by_category(rows, build_catalog.IMAGES_DIR)
            
            # Map sr_number to image details
            image_map = {}
            for cat in categories:
                for item in cat['products']:
                    image_map[item['sr_number']] = {
                        'display_image_path': item.get('display_image_path', ''),
                        'image_is_representative': item.get('image_is_representative', False)
                    }
                    
            for row in rows:
                if row['sr_number'] in image_map:
                    row['display_image_path'] = image_map[row['sr_number']]['display_image_path']
                    row['image_is_representative'] = image_map[row['sr_number']]['image_is_representative']
            
            self.send_json(200, {"fields": fields, "rows": rows, "revision": revision})
            return
        if self.path == "/api/undo/status":
            self.send_json(200, {"can_undo": bool(read_history())})
            return
        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        if not self.authorized_local_request():
            self.send_error(403, "Seller tools are available only over the local loopback server.")
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
            self.send_error(415, "Expected an application/json request.")
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > 10_000_000:
                raise ValueError("Request body must be between 1 byte and 10 MB.")
            payload = json.loads(self.rfile.read(content_length))
            if self.path == "/api/clients/add":
                added = append_client(payload)
                self.send_json(200, {"success": True, "added": added})
                return
            if self.path == "/api/bills/add":
                added = append_bill(payload)
                self.send_json(200, {"success": True, "added": added})
                return
            if self.path == "/api/bills/export":
                month = payload.get("month")
                if not month:
                    self.send_json(400, {"success": False, "error": "month required"})
                    return
                try:
                    subprocess.run([sys.executable, str(ROOT / "src" / "seller" / "export_tally.py"), month], check=True)
                    self.send_json(200, {"success": True, "message": f"Exported successfully for {month}"})
                except Exception as e:
                    self.send_json(500, {"success": False, "error": str(e)})
                return

            # POS bills -> per-org Tally DayBook/HSN -> TallyToOutputsForGST JSON.
            if self.path == "/api/gst/prepare":
                months = payload.get("months")
                if not months:
                    if payload.get("all"):
                        months = prepare_tally_files.available_months()
                    else:
                        months = [payload.get("month") or dt.date.today().strftime("%Y-%m")]
                result = prepare_tally_files.prepare(
                    months,
                    tally_repo=payload.get("tally_repo"),
                    run_converter=payload.get("run", True) is not False,
                )
                self.send_json(200 if result.get("ok") else 500,
                               {"success": bool(result.get("ok")), "result": result})
                return

            if self.path == "/api/catalog/save":
                fields, rows, revision = update_catalog(payload["rows"], payload["revision"])
                try:
                    run_updater()
                except (subprocess.CalledProcessError, OSError) as error:
                    self.send_json(500, {
                        "error": f"Catalog saved, but the one-click update checks failed: {error}",
                        "fields": fields,
                        "rows": rows,
                        "revision": revision,
                    })
                    return
                self.send_json(200, {
                    "fields": fields,
                    "rows": rows,
                    "revision": revision,
                    "message": "Catalog saved; the rebuild and full test suite passed. Run update.sh to publish.",
                })
                return
            if self.path == "/api/catalog/undo":
                fields, rows, revision = undo_catalog(payload["revision"])
                try:
                    run_updater()
                except (subprocess.CalledProcessError, OSError) as error:
                    self.send_json(500, {
                        "error": f"Undo was saved, but the one-click update checks failed: {error}",
                        "fields": fields,
                        "rows": rows,
                        "revision": revision,
                    })
                    return
                self.send_json(200, {
                    "fields": fields,
                    "rows": rows,
                    "revision": revision,
                    "message": "Undo applied successfully and one-click update checks passed.",
                })
                return
            self.send_error(404, "Unknown seller API endpoint.")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error)})


def main():
    if os.environ.get("SKUMAR_SELLER_ALLOW_NONLOOPBACK") == "1":
        raise RuntimeError("The seller editor refuses non-loopback binding.")
    server = ThreadingHTTPServer((HOST, PORT), SellerHandler)
    server.daemon_threads = True
    print(f"Seller editor available only on this computer: http://{HOST}:{PORT}/index.html")
    print("Do not change the bind address or expose this local seller service to the network.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping the local seller editor.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
