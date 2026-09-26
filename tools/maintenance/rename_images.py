import csv
import os
import re
from pathlib import Path

os.chdir(Path(__file__).resolve().parents[2])

def sanitize_filename(name):
    # Remove invalid characters for Windows filenames
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    # Replace spaces and weird characters with underscores
    clean = re.sub(r'[\s\.\-]+', "_", clean)
    # Remove leading/trailing underscores
    clean = clean.strip('_')
    # Limit length
    return clean[:100]

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

images_dir = Path('images')

for row in rows:
    img_ref = row['image_ref']
    if not img_ref: continue
    
    if img_ref.startswith('item_'):
        # It's an inline image, let's rename it to something meaningful
        sr = row['sr_no']
        item_name = row['item_name']
        
        # New name format: sr_123_teflon_tube_2mm
        new_ref = f"sr_{sr}_{sanitize_filename(item_name)}"
        
        # Find the actual file on disk
        for ext in ['.png', '.jpg', '.jpeg']:
            old_path = images_dir / f"{img_ref}{ext}"
            new_path = images_dir / f"{new_ref}{ext}"
            
            if old_path.exists():
                try:
                    os.rename(old_path, new_path)
                    row['image_ref'] = new_ref
                except Exception as e:
                    print(f"Error renaming {old_path} to {new_path}: {e}")
                break

with open('data/catalog_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("Images renamed successfully based on item names!")
