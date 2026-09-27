#!/usr/bin/env python3
"""
Build Catalog - Generates HTML catalogs from CSV data and images.

Usage:
    python build_catalog.py

Reads:
    - data/config.json  : Company info and settings
    - data/catalog_data.csv : Product data
    - images/           : Product images
    - templates/        : Jinja2 HTML templates

Produces:
    - print_catalog.html  : Full print-ready catalog
    - search_catalog.html : Local seller catalog
    - customer_catalog.html : Customer-facing searchable catalog
"""

import csv
import json
import os
import sys
import math
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    print("Installing jinja2...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "jinja2"])
    from jinja2 import Environment, FileSystemLoader, select_autoescape


# ============================================================
# Paths
# ============================================================
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "data" / "config.json"
DATA_FILE = SCRIPT_DIR / "data" / "catalog_data.csv"
DATA_NOTES_FILE = SCRIPT_DIR / "data" / "catalog_data_notes.json"
IMAGES_DIR = SCRIPT_DIR / "images"
TEMPLATES_DIR = SCRIPT_DIR / "templates"
OUTPUT_DIR = SCRIPT_DIR


def load_config():
    """Load company configuration."""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_csv_data(csv_path):
    """Load product data from CSV."""
    items = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        required_fields = {
            'sr_number', 'category', 'item_name', 'hsn_code', 'list_price',
            'unit', 'packing', 'image_ref', 'page'
        }
        missing_fields = required_fields - set(reader.fieldnames or [])
        if missing_fields:
            raise ValueError(f"Catalog CSV is missing columns: {', '.join(sorted(missing_fields))}")

        for row in reader:
            # Clean up data
            item = {}
            for key, val in row.items():
                item[key] = val.strip() if val else ''
            
            if not item.get('sr_number') or not item.get('sr_number', '').strip():
                continue

            item['hidden'] = item.get('hidden', '').strip().lower() in {
                '1', 'true', 'yes', 'hidden'
            }
            
            # Clean up unit field
            unit = item.get('unit', '')
            if unit in (',,', ',') or '\ufffd' in unit:
                item['unit'] = ''
            if '\ufffd' in item.get('packing', ''):
                item['packing'] = ''
                
            item['image_path'] = find_image(item.get('image_ref', ''), IMAGES_DIR)
            
            items.append(item)

    validate_catalog_data(items)
    notes = load_catalog_data_notes(items)
    for item in items:
        item['notes'] = notes.get(item['sr_number'], {})
    return items


def load_catalog_data_notes(items):
    """Load source ambiguities without mixing explanatory notes into price values."""
    if not DATA_NOTES_FILE.exists():
        return {}

    with DATA_NOTES_FILE.open('r', encoding='utf-8') as f:
        notes = json.load(f)
    if not isinstance(notes, dict):
        raise ValueError("Catalog data notes must be a JSON object keyed by serial number.")

    valid_serials = {item['sr_number'] for item in items}
    unknown_serials = set(notes) - valid_serials
    if unknown_serials:
        raise ValueError(f"Catalog notes reference unknown serials: {', '.join(sorted(unknown_serials))}")
    return notes


def visible_catalog_items(items):
    return [item for item in items if not item.get('hidden', False)]


def validate_catalog_data(items):
    """Reject duplicate identifiers and malformed prices while allowing quote-only items."""
    serials = []
    for item in items:
        serial = item.get('sr_number', '')
        try:
            group_str, item_str = serial.split('.')
            group_number = int(group_str)
            item_number = int(item_str)
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise ValueError(f"Invalid catalog serial number: {serial!r}") from error
        if group_number < 1 or item_number < 1:
            raise ValueError(f"Catalog serial number must have positive parts: {serial}.")
        serials.append(serial)

        if not item.get('category') or not item.get('item_name'):
            raise ValueError(f"Catalog item {serial} needs a category and item name.")

        price = item.get('list_price', '').strip()
        if price:
            try:
                amount = Decimal(price)
            except InvalidOperation as error:
                raise ValueError(f"Invalid price for catalog item {serial}: {price!r}") from error
            if not amount.is_finite() or amount < 0:
                raise ValueError(f"Price for catalog item {serial} must be finite and non-negative.")

    if len(serials) != len(set(serials)):
        raise ValueError("Catalog serial numbers must be unique.")


def find_image(image_ref, images_dir):
    """Find an image file by its reference name (without extension)."""
    if not image_ref:
        return None
    
    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
        img_path = images_dir / f"{image_ref}{ext}"
        if img_path.exists():
            return img_path.relative_to(images_dir.parent).as_posix()
    
    return None


def group_by_category(items, images_dir):
    """Group items by category and attach image info."""
    categories = OrderedDict()
    
    for item in items:
        cat_name = item.get('category', 'Uncategorized')
        if not cat_name:
            cat_name = 'Uncategorized'
        
        if cat_name not in categories:
            image_ref = item.get('image_ref', '')
            image_path = find_image(image_ref, images_dir)
            
            categories[cat_name] = {
                'name': cat_name,
                'image_ref': image_ref,
                'image_path': image_path,
                'products': []
            }
        
        categories[cat_name]['products'].append(item)

    for category in categories.values():
        for item in category['products']:
            item['display_image_path'] = item.get('image_path') or category['image_path']
            item['image_is_representative'] = not bool(item.get('image_path')) and bool(category['image_path'])
    
    return list(categories.values())


def paginate_categories(categories, items_per_page=60):
    """Split categories into pages for the print catalog."""
    pages = []
    current_page = []
    current_count = 0
    
    for cat in categories:
        cat_size = len(cat['products']) + 1  # +1 for header row
        
        if current_count + cat_size > items_per_page and current_page:
            pages.append(current_page)
            current_page = []
            current_count = 0
        
        current_page.append(cat)
        current_count += cat_size
    
    if current_page:
        pages.append(current_page)
    
    return pages


def write_html_output(output_path, html):
    """Write generated HTML without carrying template indentation onto blank lines."""
    normalized_html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(normalized_html)


def build_print_catalog(config, categories, env):
    """Generate the print-ready HTML catalog."""
    template = env.get_template('print_template.html')
    
    items_per_page = config.get('items_per_page', 60)
    pages = paginate_categories(categories, items_per_page)
    
    html = template.render(
        company=config['company'],
        categories=categories,
        pages=pages,
        terms=config.get('terms', ''),
        generation_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        images_base='images'
    )
    
    output_path = OUTPUT_DIR / 'print_catalog.html'
    write_html_output(output_path, html)
    
    print(f"  [OK] Print catalog: {output_path}")
    return output_path


import unicodedata

def normalize_search_text(text):
    if not text:
        return ""
    # Remove diacritics and make lowercase
    text = str(text)
    normalized = ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )
    return normalized.lower().strip()

def prepare_search_catalog_data(items):
    """Retain CSV fields and public display paths in the machine-readable catalog payload, excluding private image_path."""
    processed = []
    for item in items:
        clean_item = {key: value for key, value in item.items() if key != 'image_path'}
        
        search_parts = [
            clean_item.get('item_name', ''),
            clean_item.get('category', ''),
            clean_item.get('hsn_code', ''),
            clean_item.get('sr_number', ''),
            clean_item.get('size', ''),
            clean_item.get('id_size', ''),
            clean_item.get('od_size', ''),
            clean_item.get('lf_size', '')
        ]
        clean_item['search_text'] = normalize_search_text(' '.join(filter(None, search_parts)))
        processed.append(clean_item)
        
    return processed


def build_search_catalog(config, categories, items, env, seller_mode=False):
    """Generate a customer or local seller searchable catalog."""
    template = env.get_template('search_template.html')
    catalog_data = prepare_search_catalog_data(items)
    
    # Get unique category names
    category_names = list(OrderedDict.fromkeys(
        item.get('category', '') for item in items if item.get('category')
    ))
    
    html = template.render(
        company=config['company'],
        billing=config,
        categories=categories,
        catalog_data=catalog_data,
        category_names=sorted(category_names),
        generation_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        images_base='images',
        seller_mode=seller_mode,
    )
    output_path = OUTPUT_DIR / ('search_catalog.html' if seller_mode else 'customer_catalog.html')
    write_html_output(output_path, html)
    
    print(f"  [OK] Search catalog: {output_path}")
    return output_path


def main():
    print("=" * 60)
    print("  GSC / S.Kumar Catalog Builder")
    print("=" * 60)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load config
    print("\n1. Loading configuration...")
    config = load_config()
    print(f"   Company: {config['company']['name']}")
    print(f"   Date: {config['company']['date']}")
    
    # Load data
    print("\n2. Loading product data...")
    items = load_csv_data(DATA_FILE)
    active_items = visible_catalog_items(items)
    print(f"   Loaded {len(items)} items ({len(active_items)} visible; {len(items) - len(active_items)} hidden)")
    
    # Group by category
    print("\n3. Grouping by category...")
    categories = group_by_category(active_items, IMAGES_DIR)
    print(f"   {len(categories)} categories found")
    for cat in categories:
        print(f"     - {cat['name']}: {len(cat['products'])} items" + 
              (f" (image: {cat['image_ref']})" if cat['image_ref'] else ""))
    
    # Setup Jinja2
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Build catalogs
    print("\n4. Generating catalogs...")
    
    print_path = build_print_catalog(config, categories, env)
    customer_path = build_search_catalog(config, categories, active_items, env)
    seller_categories = group_by_category(items, IMAGES_DIR)
    seller_path = build_search_catalog(config, seller_categories, items, env, seller_mode=True)
    
    # Summary
    print("\n" + "=" * 60)
    print("  BUILD COMPLETE!")
    print("=" * 60)
    print(f"\n  Items: {len(items)}")
    print(f"  Categories: {len(categories)}")
    print(f"\n  Output files:")
    print(f"    Print catalog:  {print_path}")
    print(f"    Customer catalog: {customer_path}")
    print(f"    Local seller catalog: {seller_path}")
    print(f"\n  Open the HTML files in a browser to view!")
    print(f"  Print catalog -> Ctrl+P -> Save as PDF for sharing")
    
    if os.environ.get('CATALOG_NO_BROWSER') != '1':
        try:
            import webbrowser
            webbrowser.open("http://127.0.0.1:8766/search_catalog.html")
            print("\n  [OK] Opened seller catalog (start tools/seller/start_seller.bat first)")
        except Exception:
            pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
