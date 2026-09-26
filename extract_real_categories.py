from docx import Document
from pathlib import Path
import re

doc = Document(Path(__file__).resolve().parent / 'List 2025.docx')

categories = []
current_cat = "Unknown"

for t in doc.tables:
    for row in t.rows:
        try:
            cells = row.cells
            sr1 = cells[0].text.strip()
            part1 = cells[1].text.strip().replace('\n', ' ')
            
            # Check if this row is a category header
            if not sr1 and len(part1) > 2 and not part1.startswith('HSN') and not "Sr.No" in part1 and not "S. KUMAR" in part1 and not part1.isupper() and len(part1) < 80:
                # wait, some categories ARE uppercase.
                # Let's just check if it's bold or has no sr1
                pass
                
            # Actually, simpler: if not sr1 and part1 has length: it's a header.
            if not sr1 and len(part1) > 3 and not part1.startswith('HSN') and "Office Phone" not in part1:
                current_cat = part1.strip()
                
            elif sr1.isdigit():
                # Store the mapping!
                categories.append((int(sr1), current_cat, part1[:30]))
        except: pass

with open('cat_ranges.txt', 'w', encoding='utf-8') as f:
    last_cat = None
    for sr, cat, part in categories:
        if cat != last_cat:
            f.write(f"SR {sr} -> {cat} ({part})\n")
            last_cat = cat
