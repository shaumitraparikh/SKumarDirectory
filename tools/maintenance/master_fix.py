from pathlib import Path
import os
import csv

os.chdir(Path(__file__).resolve().parents[2])

# The PERFECT mapping based on docx analysis
def get_true_category(sr):
    if sr < 1020: return None # leave as is
    if 1020 <= sr <= 1081: return "PVC Ferrules Marking"
    if 1082 <= sr <= 1100: return "Bulb & Indicator & LED Resistance"
    if 1101 <= sr <= 1107: return "Glass & Ceramics Fuses"
    if 1108 <= sr <= 1150: return "Push Button Switch & Box"
    if 1151 <= sr <= 1168: return "Computer Power Cords & Prods"
    if 1169 <= sr <= 1232: return "PVC & Cotton Cords"
    if 1233 <= sr <= 1257: return "SATO / Imported Rocker Switch"
    if 1258 <= sr <= 1283: return "SATO & SURAJ Toggle Switches"
    if 1284 <= sr <= 1301: return "Regulators & Knobs"
    if 1302 <= sr <= 1315: return "Adaptors & Power Supplies"
    if 1316 <= sr <= 1324: return "Toy Motors & Accessories"
    if 1325 <= sr <= 1341: return "Water Seals & Pipes"
    if 1342 <= sr <= 1360: return "Bulbs & Holders"
    if 1361 <= sr <= 1379: return "Audio Video & HDMI Cords"
    if 1380 <= sr <= 1385: return "Step-Down Voltage Converters"
    if 1386 <= sr <= 1391: return "Hand Gloves"
    if 1392 <= sr <= 1395: return "Danger Plates"
    if 1396 <= sr <= 1399: return "MCB Links"
    if 1400 <= sr <= 1402: return "DC Locks & Keys"
    if 1403 <= sr <= 1410: return "Rubber Gromet"
    if sr == 1411: return "Rubber Border Biding Patti"
    return "DELETE"

IMG_MAP = {
    "ART SILK TUBE / Sleeves": "art_silk_tube_sleeves",
    "FIBREGLASS B CLASS YELLOW TUBE": "fibreglass_b_class_yellow_tube",
    "FIBREGLASS B CLASS WHITE SPECIAL TUBE": "fibreglass_b_class_white_special_tube",
    "FIBREGLASS F CLASS TUBE": "fibreglass_f_class_tube",
    "FIBREGLASS PVC COATED CHINA TUBE": "fibreglass_pvc_coated_china_tube",
    "FIBREGLASS SILICON H CLASS CHINA TUBE": "fibreglass_silicon_h_class_china_tube",
    "PVC CORD AND PIPES": "pvc_pipes",
    "Rubber Type Heat Shrinkable Tubing": "p_v_c_heat_shinkable_tube",
    "TEFLON TUBE": "teflon_tube",
    "PVC Flexible Pipe": "pvc_flexible_pipe",
    "PVC Flexible Pipe Adaptor": "pvc_flexible_pipe_adaptor",
    "Galvanised Flexible Pipe": "pvc_flexible_pipe",
    "M a r k i n g P r i n t i n g S l e v e / T u b i n g": "m_a_r_k_i_n_g_p_r_i_n_t_i_n_g",
    "PVC Channel Box": "pvc_channel_box",
    "TEFLON CABLE": "teflon_cable",
    "Telephone Products & Accessories": "telephone_products_accessories",
    "PVC Sealer Automatic Machine & Parts": "pvc_sealer_automatic_machine_parts",
    "Battery & Accessaries": "battery_accessories",
    "Battery Terminal, Lugs & Clips h": "battery_accessories",
    "C u t t e r & B l a d e s": "taparia_tools",
    "Plier Stripper & C u t t e r": "taparia_tools",
    "Kundip Items": "kundip_items",
    "Ceramic Sonyee Mony/Beads": "kundip_items",
    "Soldron Items": "soldron_items",
    "RedPlus MALA Soldering Items": "soldron_items",
    "Toni Soldering Items": "soldron_items",
    "SOLDER STICK": "soldron_items",
    "Joint Solder Wire in 18, 22swg": "soldron_items",
    "Khosla Solder Wire in 14,16,18,22swg": "soldron_items",
    "KUMAR Solder Wire in 14,16,18,22swg": "soldron_items",
    "Soldering Paste & Liquied": "soldron_items",
    "Solder Pot": "soldron_items",
    "Heat Sink Compound": "soldron_items",
    "Puller Metal Wire": "taparia_tools",
    "Nylon Cable Tie In White & Black Colour": "nylon_cable_tie",
    "PVC Ferrules Marking": "taparia_tools", # Actually, maybe nylon_cable_tie or none. Let's just use none.
    "Bulb & Indicator & LED Resistance": "battery_accessories",
    "Glass & Ceramics Fuses": "tinned_copper_fuse_wire",
    "Push Button Switch & Box": "ax_items",
    "PVC & Cotton Cords": "pvc_cord",
    "SATO / Imported Rocker Switch": "tinned_copper_fuse_wire", # remove this mapping! Wait, tinned fuse wire is not rocker switch.
    "SATO & SURAJ Toggle Switches": "ax_items", # remove!
}

# Clean mappings (only keep existing images)
import os
existing_imgs = [f.split('.')[0] for f in os.listdir('images') if f.endswith('.png') or f.endswith('.jpeg') or f.endswith('.jpg')]

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

new_rows = []
for row in rows:
    if not row['sr_no'].isdigit(): 
        new_rows.append(row)
        continue
        
    sr = int(row['sr_no'])
    
    true_cat = get_true_category(sr)
    if true_cat == "DELETE":
        continue
        
    if true_cat:
        # If it was assigned a wrong category, the item_name probably got the wrong category prepended to it!
        # E.g. "SATO , SURAJ Toggle Switches 250 Volts AC Maxicom Cord"
        # We must strip the old wrong category!
        old_cat = row['category']
        if old_cat in row['item_name']:
            row['item_name'] = row['item_name'].replace(old_cat, '').strip()
            
        row['category'] = true_cat
        
        # Prepend NEW category if it's missing and name is short or just size
        if true_cat.lower() not in row['item_name'].lower():
            words = row['item_name'].split()
            cat_words = true_cat.split()
            if not (words and cat_words and words[0].lower() == cat_words[0].lower()):
                row['item_name'] = f"{true_cat} {row['item_name']}".strip()
                
    # Fix image_ref
    img = row['image_ref']
    if not img.startswith('item_'):
        # Only assign if it exists in a strict map and the file actually exists!
        cat_clean = row['category'].replace('', '').replace(' ', '').lower()
        # Instead of fuzzy matching, we'll just strictly map using a verified dictionary
        row['image_ref'] = ""
        for m_cat, m_img in IMG_MAP.items():
            if m_cat.replace(' ', '').lower() in cat_clean or cat_clean in m_cat.replace(' ', '').lower():
                if m_img in existing_imgs and m_img not in ['taparia_tools', 'ax_items', 'kundip_items', 'soldron_items']:
                    row['image_ref'] = m_img
                    break
        
        # Override some known bad maps
        if "switch" in row['category'].lower() or "rocker" in row['category'].lower():
            row['image_ref'] = "" # We don't have switch images
        if "ferrule" in row['category'].lower():
            row['image_ref'] = ""

    new_rows.append(row)

with open('data/catalog_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=new_rows[0].keys())
    writer.writeheader()
    writer.writerows(new_rows)

print(f"Data perfectly fixed! Reduced items from {len(rows)} to {len(new_rows)}.")
