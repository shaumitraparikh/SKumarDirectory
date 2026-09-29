import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data'
CATALOG_FILE = DATA_DIR / 'catalog_data.csv'
MAP_FILE = DATA_DIR / 'image_serial_map.json'
IMAGES_DIR = ROOT / 'images'

existing_images = {p.stem for p in IMAGES_DIR.glob('*.*')}

with open(CATALOG_FILE, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    items = list(reader)

# Group existing images by group prefix
group_images = {}
for stem in existing_images:
    parts = stem.split('.')
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        group_images.setdefault(int(parts[0]), []).append((int(parts[1]), stem))

for grp in group_images:
    group_images[grp].sort()

# Category to existing image mapping
category_images = {}
for it in items:
    cat = it.get('category')
    ref = it.get('image_ref')
    if cat and ref and ref in existing_images and cat not in category_images:
        category_images[cat] = ref

def resolve_image(sr, cat):
    parts = sr.split('.')
    try:
        grp = int(parts[0])
        num = int(parts[1]) if len(parts) > 1 else 1
    except ValueError:
        grp = 1
        num = 1
        
    # Check within same group prefix
    if grp in group_images and group_images[grp]:
        imgs = group_images[grp]
        cand = None
        for n_img, stem in imgs:
            if n_img <= num:
                cand = stem
            else:
                break
        if cand is None:
            cand = imgs[0][1]
        return cand
        
    # Proximity mappings in list Sr No
    if grp == 35:
        return '36.1'
    if grp == 64:
        return '63.6'
    if grp == 65:
        return '56.1'
        
    if cat in category_images:
        return category_images[cat]
        
    all_grps = sorted(group_images.keys())
    closest_grp = min(all_grps, key=lambda g: abs(g - grp))
    return group_images[closest_grp][0][1]

# Assign image to items where missing
updated_count = 0
for it in items:
    current_ref = it.get('image_ref', '').strip()
    if not current_ref or current_ref not in existing_images:
        it['image_ref'] = resolve_image(it['sr_number'], it.get('category'))
        updated_count += 1

# Write back catalog_data.csv
with open(CATALOG_FILE, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(items)

print(f"Updated {updated_count} items in catalog_data.csv.")

# Rebuild image_serial_map.json
image_map = {}
for it in items:
    ref = it.get('image_ref')
    if ref:
        image_map.setdefault(ref, {"group_items": []})
        if it['sr_number'] not in image_map[ref]["group_items"]:
            image_map[ref]["group_items"].append(it['sr_number'])

# Ensure all files on disk are keys in the map
for stem in sorted(existing_images):
    if stem not in image_map:
        image_map[stem] = {"group_items": []}

with open(MAP_FILE, 'w', encoding='utf-8') as f:
    json.dump(image_map, f, indent=2)

print(f"Updated image_serial_map.json with {len(image_map)} keys.")
