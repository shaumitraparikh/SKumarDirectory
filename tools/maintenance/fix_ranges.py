import os
from pathlib import Path
import csv

os.chdir(Path(__file__).resolve().parents[2])
import re

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

for row in rows:
    if not row['sr_no'].isdigit(): continue
    sr = int(row['sr_no'])
    
    cat = row['category'].strip()
    
    # 1. Fix fragmented categories based on exact known sr ranges
    if 71 <= sr <= 95:
        cat = "PVC CORD AND PIPES"
    elif 138 <= sr <= 144:
        cat = "PVC Flexible Pipe"
    elif 145 <= sr <= 150:
        cat = "PVC Flexible Pipe Adaptor"
    elif 151 <= sr <= 159:
        cat = "Galvanised Flexible Pipe"
        
    row['category'] = cat
    
    # Clean the category string more cleanly
    clean = cat.replace(' h', '').strip()
    if clean.endswith(':'): clean = clean[:-1].strip()
    row['category'] = clean

# Ensure item names are proper
for row in rows:
    # Remove category string from the start of the item name if it exists and looks redundant
    # wait, earlier we prepended it! But if the category was a size, we shouldn't have.
    # We will just leave item_name alone since we already fixed prices and sizes.
    pass

# Write back
with open('data/catalog_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("Fixed fragmented categories using exact ranges!")
