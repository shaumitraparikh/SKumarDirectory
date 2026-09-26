import json

with open("docx_rows.json") as f:
    docx_rows = json.load(f)

# Group by table: we can just print the header of each table.
# A table usually starts with a row containing "Sr.No." or similar.
tables = []
current_table = []
for r in docx_rows:
    if "Sr.No." in r or "P A R T I C U L A R S" in r:
        if current_table:
            tables.append(current_table)
        current_table = [r]
    elif current_table:
        current_table.append(r)

if current_table:
    tables.append(current_table)

for i, t in enumerate(tables):
    print(f"Table {i+1} has {len(t)} rows. Header: {t[0]}")
    
