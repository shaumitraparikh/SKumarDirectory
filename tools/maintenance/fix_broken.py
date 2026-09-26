import csv
import os
from pathlib import Path
import re

os.chdir(Path(__file__).resolve().parents[2])

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

images_dir = Path('images')
all_images = [p.stem for p in images_dir.glob('*') if p.is_file()]

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|]', '', name)
    clean = re.sub(r'[\s\.\-]+', '_', clean)
    return clean.strip('_')[:100]

categories = {}
for row in rows:
    cat = row['category']
    sr = int(row['sr_no'])
    if cat not in categories:
        categories[cat] = {'min_sr': sr, 'max_sr': sr}
    else:
        categories[cat]['min_sr'] = min(categories[cat]['min_sr'], sr)
        categories[cat]['max_sr'] = max(categories[cat]['max_sr'], sr)

fixes = 0
for row in rows:
    img = row['image_ref']
    if img and not img.startswith('sr_') and not img.startswith('group_'):
        # It was a group image. Let's see if we can find the new name.
        cat = row['category']
        c_min = categories[cat]['min_sr']
        c_max = categories[cat]['max_sr']
        expected_new_name = f"group_sr_{c_min}_to_{c_max}_{sanitize_filename(cat)}"
        
        if expected_new_name in all_images:
            row['image_ref'] = expected_new_name
            fixes += 1
        else:
            s_cat = sanitize_filename(cat)
            for existing in all_images:
                if s_cat in existing and existing.startswith('group_'):
                    row['image_ref'] = existing
                    fixes += 1
                    break

with open('data/catalog_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f'Fixed {fixes} broken image references in CSV!')
