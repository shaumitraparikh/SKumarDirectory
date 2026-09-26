import os
from pathlib import Path
import csv
import re

os.chdir(Path(__file__).resolve().parents[2])

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

for row in rows:
    if row['category'] == 'General Items':
        print(f"{row['sr_no']} | {row['item_name']} | {row['image_ref']}")
