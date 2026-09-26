import os
from pathlib import Path
import csv

os.chdir(Path(__file__).resolve().parents[2])

cats = {}
with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if not r['sr_no'].isdigit(): continue
        sr = int(r['sr_no'])
        c = r['category']
        if c not in cats: cats[c] = []
        cats[c].append(sr)

for c, srs in cats.items():
    print(f"{c}: {min(srs)} - {max(srs)} ({len(srs)} items)")
