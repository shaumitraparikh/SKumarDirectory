#!/usr/bin/env python3
"""Loopback-only catalog editor and safe CSV persistence service."""

import csv
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
DATA_FILE = ROOT / "data" / "catalog_data.csv"
HISTORY_FILE = ROOT / "data" / ".seller_history.json"
HOST = "127.0.0.1"
PORT = 8766
MAX_HISTORY = 50

sys.path.insert(0, str(ROOT))
import build_catalog



CLIENT_FILE = ROOT / "data" / "client_data.csv"

def read_clients():
    if not CLIENT_FILE.exists():
        return []
    with CLIENT_FILE.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))

def append_client(new_client):
    clients = read_clients()
    gstin = new_client.get('gstin', '').strip()
    name = new_client.get('name', '').strip()
    
    updated_existing = False
    for c in clients:
        # Match by GSTIN or Name (case-insensitive)
        if (gstin and c.get('gstin') == gstin) or (name and c.get('name', '').lower() == name.lower()):
            updated_existing = True
            # Update any missing fields
            for k in ['phone', 'email', 'address', 'state', 'pincode', 'gstin']:
                if new_client.get(k) and not c.get(k):
                    c[k] = new_client.get(k)
            break
            
    fieldnames = ['client_id','name','business_name','phone','email','address','state','pincode','gstin']
    
    if not updated_existing:
        if not new_client.get('client_id'):
            new_client['client_id'] = gstin if gstin else name.upper().replace(' ', '_')[:10]
        # Only keep known fields
        clean_new = {k: new_client.get(k, '') for k in fieldnames}
        clients.append(clean_new)

    # Rewrite the whole file to save updates
    with CLIENT_FILE.open(mode='w', encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in clients:
            writer.writerow({k: c.get(k, '') for k in fieldnames})
            
    return True


def read_catalog():
    raw = DATA_FILE.read_bytes()
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
        if set(row) != allowed_fields:
            raise ValueError("Each product must contain exactly the catalog's current fields.")
        item = {field: str(row.get(field, "")).strip() for field in fields}
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
    if os.name != "nt":
        command = [
            sys.executable,
            str(ROOT / "build_catalog.py"),
        ]
        subprocess.run(command, cwd=ROOT, check=True)
        subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            cwd=ROOT,
            check=True,
        )
        for test_file in ("order_core.test.js", "client_directory.test.js", "bill_archive.test.js"):
            subprocess.run(["node", f"tests/{test_file}"], cwd=ROOT, check=True)
        return
    subprocess.run(
        [str(ROOT / "1_Click_Update.bat")],
        cwd=ROOT,
        check=True,
        shell=True,
    )


class SellerHandler(SimpleHTTPRequestHandler):
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
        if origin and origin not in {
            f"http://127.0.0.1:{PORT}",
            f"http://localhost:{PORT}",
        }:
            return False
        return True

    def do_GET(self):
        if not self.authorized_local_request():
            self.send_error(403, "Seller tools are available only over the local loopback server.")
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
            self.path = "/search_catalog.html"
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
                    "message": "Catalog saved; 1_Click_Update rebuilt the pages and passed its tests. Run the publisher to publish.",
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
    print(f"Seller editor available only on this computer: http://{HOST}:{PORT}/search_catalog.html")
    print("Do not change the bind address or expose this local seller service to the network.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping the local seller editor.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
