import os
from pathlib import Path
import csv

os.chdir(Path(__file__).resolve().parents[2])

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if 'HSN' in row['item_name'].upper() or 'HSN' in row['category'].upper():
            print(f"{row['sr_no']} | Cat: {row['category']} | Name: {row['item_name']}")
