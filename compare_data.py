import pandas as pd
import json
import re

# Read CSV
df = pd.read_csv("data/catalog_data.csv")
csv_items = []
for idx, row in df.iterrows():
    csv_items.append({
        "sr_number": str(row["sr_number"]),
        "item_name": str(row["item_name"]).strip(),
        "list_price": str(row["list_price"]).strip() if pd.notna(row["list_price"]) else "",
        "unit": str(row["unit"]).strip() if pd.notna(row["unit"]) else "",
        "hsn_code": str(row["hsn_code"]).strip() if pd.notna(row["hsn_code"]) else "",
    })

# Read docx rows
with open("docx_rows.json") as f:
    docx_rows = json.load(f)

docx_items = []
current_hsn = ""
for row in docx_rows:
    # A row might have multiple sets of (Sr.No., Particulars, ..., List, Per)
    # They can be structured as:
    # ['460', '', '1.50V Button Cell...', '1.50V Button Cell...', '16.00', ',,', '534', 'Side Cutting...', '82032000', '253.00', ',,']
    # Let's extract by looking for cells that are purely numeric or digit+letter (like '1', '2A', etc.)
    
    # We will try a heuristic: iterate through cells.
    # If a cell is numeric (or mostly numeric like '46A'), and the next few cells have text and price...
    # Actually, we can just look at the header of each table.
    pass
