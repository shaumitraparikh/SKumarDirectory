import os
from pathlib import Path
import csv

os.chdir(Path(__file__).resolve().parents[2])

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['image_ref'].startswith('item_'):
            print(f"{r['sr_number']} | {r['item_name']} | {r['image_ref']}")
