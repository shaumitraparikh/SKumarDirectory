import os
from pathlib import Path
import csv

os.chdir(Path(__file__).resolve().parents[2])

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

for row in rows:
    cat = row['category'].strip()
    name = row['item_name'].strip()
    
    # 1. Strip exact price from end of name
    price = row['list_price'].strip()
    if price and name.endswith(price):
        name = name[:-len(price)].strip()
    try:
        pf = f"{float(price):.2f}"
        if name.endswith(pf):
            name = name[:-len(pf)].strip()
    except:
        pass
        
    # 2. Add group name to item name if not present
    if cat and cat.lower() not in name.lower():
        # Avoid prepending if it's already very similar (e.g. "Solder Pot" and "Solder Pot Model 11C")
        # Check if the first word of category matches first word of name
        cat_words = cat.split()
        name_words = name.split()
        if cat_words and name_words and cat_words[0].lower() == name_words[0].lower():
            pass # Probably already contains it or starts with it
        else:
            name = f"{cat} {name}"
            
    row['item_name'] = name

with open('data/catalog_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("Names updated with group names perfectly!")
