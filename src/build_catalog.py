#!/usr/bin/env python3
"""
Build Catalog - Generates HTML catalogs from CSV data and images.

Usage:
    python src/build_catalog.py

Reads:
    - data/config.json  : Company info and settings
    - data/catalog_data.csv : Product data
    - images/           : Product images
    - app/templates/    : Jinja2 HTML templates

Produces (repo root):
    - index.html          : Interactive POS / search catalog
    - print_catalog.html  : Print-ready price list
    - photo_catalog.html  : Visual photo catalog

Customer directory (data/client_data.csv) is never embedded in public HTML.
Staff load it locally via the checkout "Load Customer List" control.
"""

import csv
import hashlib
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
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_FILE = SCRIPT_DIR / "data" / "config.json"
DATA_FILE = SCRIPT_DIR / "data" / "catalog_data.csv"
DATA_NOTES_FILE = SCRIPT_DIR / "data" / "catalog_data_notes.json"
IMAGES_DIR = SCRIPT_DIR / "images"
TEMPLATES_DIR = SCRIPT_DIR / "app" / "templates"
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
    """Group items by category and attach image info according to list Sr No."""
    categories = OrderedDict()
    
    # Index available images by numeric group and item number
    group_images = {}
    for p in images_dir.glob('*.*'):
        stem = p.stem
        parts = stem.split('.')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            rel_path = p.relative_to(images_dir.parent).as_posix()
            group_images.setdefault(int(parts[0]), []).append((int(parts[1]), rel_path))

    for grp in group_images:
        group_images[grp].sort()

    def find_image_for_sr(sr, fallback_cat_img):
        parts = sr.split('.')
        try:
            grp = int(parts[0])
            num = int(parts[1]) if len(parts) > 1 else 1
        except ValueError:
            grp = 1
            num = 1
            
        if grp in group_images and group_images[grp]:
            imgs = group_images[grp]
            cand = None
            for n_img, path in imgs:
                if n_img <= num:
                    cand = path
                else:
                    break
            if cand is None:
                cand = imgs[0][1]
            return cand
            
        if fallback_cat_img:
            return fallback_cat_img
            
        # Fallbacks by Sr No proximity
        if grp == 35:
            cand = find_image('36.1', images_dir)
            if cand:
                return cand
        if grp == 64:
            cand = find_image('63.6', images_dir)
            if cand:
                return cand
        if grp == 65:
            cand = find_image('56.1', images_dir)
            if cand:
                return cand
            
        all_grps = sorted(group_images.keys())
        if all_grps:
            closest_grp = min(all_grps, key=lambda g: abs(g - grp))
            return group_images[closest_grp][0][1]
        return None
    
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
        if not category['image_path']:
            for p in category['products']:
                img = find_image(p.get('image_ref', ''), images_dir)
                if img:
                    category['image_path'] = img
                    category['image_ref'] = p.get('image_ref', '')
                    break
            if not category['image_path'] and category['products']:
                first_sr = category['products'][0]['sr_number']
                category['image_path'] = find_image_for_sr(first_sr, None)

        for item in category['products']:
            if item.get('image_path'):
                item['display_image_path'] = item['image_path']
                item['image_is_representative'] = False
            else:
                item['display_image_path'] = find_image_for_sr(item['sr_number'], category['image_path']) or category['image_path']
                item['image_is_representative'] = not bool(item.get('image_path')) and bool(item['display_image_path'])
    
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


def clean_cat_sort_key(name):
    return str(name).strip().lstrip('“"\'\u201c\u201d\u2018\u2019-–— ').lower()


def compute_catalog_version():
    hasher = hashlib.sha256()
    if DATA_FILE.exists():
        hasher.update(DATA_FILE.read_bytes())
    if CONFIG_FILE.exists():
        hasher.update(CONFIG_FILE.read_bytes())
    js_file = SCRIPT_DIR / "app" / "assets" / "js" / "search_catalog.js"
    if js_file.exists():
        hasher.update(js_file.read_bytes())
    return hasher.hexdigest()[:10]


def build_search_catalog(config, categories, items, env):
    """Generate a customer or local seller searchable catalog."""
    template = env.get_template('search_template.html')
    catalog_data = prepare_search_catalog_data(items)
    
    # Get unique category names sorted alphabetically
    category_names = list(OrderedDict.fromkeys(
        item.get('category', '') for item in items if item.get('category')
    ))
    sorted_categories = sorted(categories, key=lambda c: clean_cat_sort_key(c['name']))
    catalog_version = compute_catalog_version()

    client_data = []
    client_csv = Path('data/client_data.csv')
    if client_csv.is_file():
        with open(client_csv, 'r', encoding='utf-8') as cf:
            reader = csv.DictReader(cf)
            client_data = list(reader)


    html = template.render(
        client_data=client_data,

        company=config['company'],
        billing=config,
        categories=categories,
        sorted_categories=sorted_categories,
        catalog_data=catalog_data,
        catalog_version=catalog_version,
        category_names=sorted(category_names, key=clean_cat_sort_key),
        generation_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        images_base='images'
    )
    output_path = OUTPUT_DIR / 'index.html'
    write_html_output(output_path, html)
    
    print(f"  [OK] Search catalog: {output_path} (v={catalog_version})")
    return output_path


PHOTO_DOC_FILE = SCRIPT_DIR / "data" / "docs 2025" / "GSC - SK Catlog Photo.docx"


def extract_photo_catalog_rows():
    """Extract category panels and mapped 0.x images from GSC - SK Catlog Photo.docx."""
    if not PHOTO_DOC_FILE.exists():
        return []
    
    try:
        from docx import Document
        doc = Document(PHOTO_DOC_FILE)
        tbl = doc.tables[0]._tbl
        trs = tbl.xpath('./w:tr')
        
        rows = []
        img_idx = 0
        for r_idx in range(8, len(trs)):
            tr = trs[r_idx]
            row_cells = []
            for tc in tr.xpath('./w:tc'):
                texts = [p.text.strip() for p in tc.xpath('.//w:p') if p.text and p.text.strip()]
                if not texts or 'Office Phone' in texts[0]:
                    continue
                title = texts[0].replace('\ufffd', '"').strip()
                sub = ' '.join(texts[1:]).replace('\ufffd', '"').strip() if len(texts) > 1 else ''
                
                blips = tc.xpath('.//a:blip')
                image_paths = []
                for b in blips:
                    img_idx += 1
                    cand_png = IMAGES_DIR / f"0.{img_idx}.png"
                    cand_jpg = IMAGES_DIR / f"0.{img_idx}.jpg"
                    if cand_png.exists():
                        image_paths.append(f"images/0.{img_idx}.png")
                    elif cand_jpg.exists():
                        image_paths.append(f"images/0.{img_idx}.jpg")
                    else:
                        image_paths.append(f"images/0.{img_idx}.png")
                        
                row_cells.append({
                    'title': title,
                    'sub': sub,
                    'images': image_paths,
                    'col_count': len(tr.xpath('./w:tc'))
                })
            if row_cells:
                rows.append(row_cells)
        return rows
    except Exception as e:
        print(f"  [WARN] Photo catalog extraction note: {e}")
        return []


def build_photo_catalog(config, categories, env):
    """Generate the unified, deduplicated HTML Visual Photo Catalog."""
    template = env.get_template('photo_template.html')
    docx_rows = extract_photo_catalog_rows()
    catalog_version = compute_catalog_version()
    
    docx_cells = [cell for row in docx_rows for cell in row]
    
    def clean_name(s):
        import re
        return re.sub(r'[^a-z0-9]', '', s.lower())

    enriched_categories = []
    for cat in categories:
        cat_copy = dict(cat)
        c_norm = clean_name(cat['name'])
        best_match = None
        for dc in docx_cells:
            d_norm = clean_name(dc['title'])
            if d_norm == c_norm:
                best_match = dc
                break
            elif (d_norm in c_norm or c_norm in d_norm) and len(d_norm) > 4:
                if not best_match:
                    best_match = dc
        
        if best_match and best_match.get('images'):
            cat_copy['gallery_images'] = best_match['images']
            cat_copy['sub'] = best_match.get('sub', '')
        elif cat.get('image_path'):
            cat_copy['gallery_images'] = [cat['image_path']]
            cat_copy['sub'] = ''
        else:
            cat_copy['gallery_images'] = []
            cat_copy['sub'] = ''
        
        enriched_categories.append(cat_copy)
    
    html = template.render(
        company=config['company'],
        billing=config,
        docx_rows=docx_rows,
        categories=enriched_categories,
        catalog_version=catalog_version,
        generation_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        images_base='images'
    )
    output_path = OUTPUT_DIR / 'photo_catalog.html'
    write_html_output(output_path, html)
    
    print(f"  [OK] Photo catalog: {output_path} (v={catalog_version})")
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
    seller_categories = group_by_category(items, IMAGES_DIR)
    customer_path = build_search_catalog(config, seller_categories, items, env)
    photo_path = build_photo_catalog(config, categories, env)
    
    # Summary
    print("\n" + "=" * 60)
    print("  BUILD COMPLETE!")
    print("=" * 60)
    print(f"\n  Items: {len(items)}")
    print(f"  Categories: {len(categories)}")
    print(f"\n  Output files:")
    print(f"    Print catalog:       {print_path}")
    print(f"    Interactive catalog: {customer_path}")
    print(f"    Photo catalog:       {photo_path}")
    print(f"\n  Open the HTML files in a browser to view!")
    print(f"  Print catalog -> Ctrl+P -> Save as PDF for sharing")
    
    if os.environ.get('CATALOG_NO_BROWSER') != '1' and os.environ.get('CI') != 'true':
        try:
            import webbrowser
            webbrowser.open(customer_path.as_uri())
        except Exception:
            pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
