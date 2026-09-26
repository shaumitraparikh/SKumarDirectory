import csv
import re

def clean_cat(cat):
    # Remove weird table header artifacts from categories
    removals = [
        " I.D.Size", " Bundle", " Cable Size", " Size Height x Weight", 
        " Size Awg mm Sqmm", " No. I.D. O.D. Qty.", " Hsn Code", 
        " Size Wire OD mm", " mm Size"
    ]
    for r in removals:
        cat = cat.replace(r, "")
    return cat.strip()

# Broader keyword matching for images
IMG_KEYWORDS = {
    "ART SILK": "art_silk_tube_sleeves",
    "FIBREGLASS B CLASS YELLOW": "fibreglass_b_class_yellow_tube",
    "FIBREGLASS B CLASS WHITE": "fibreglass_b_class_white_special_tube",
    "FIBREGLASS F CLASS": "fibreglass_f_class_tube",
    "CHINA TUBE": "fibreglass_pvc_coated_china_tube",
    "SILICON H CLASS": "fibreglass_silicon_h_class_china_tube",
    "P V C , COTTON CORDS": "pvc_cord",
    "PVC CORD": "pvc_cord",
    "PVC PIPES": "pvc_pipes",
    "HEAT SHRINKABLE": "p_v_c_heat_shinkable_tube",
    "SILICON RUBBER": "silicon_rubber_teflon_tube",
    "TEFLON TUBE": "teflon_tube",
    "FLEXIBLE PIPE ADAPTOR": "pvc_flexible_pipe_adaptor",
    "FLEXIBLE PIPE": "pvc_flexible_pipe",
    "GALVANISHED": "galvanished_g_i_flexible_pipe",
    "MARKING": "m_a_r_k_i_n_g_p_r_i_n_t_i_n_g",
    "PE SPIRAL": "pe_spiral_wrapping_tube",
    "CHANNEL BOX": "pvc_channel_box",
    "VARNISHED CABLE": "fiber_glass_varnished_cable",
    "TEFLON CABLE": "teflon_cable",
    "COPPER FUSE WIRE": "tinned_copper_fuse_wire",
    "VARNISH": "insulating_varnish",
    "COOLING FAN": "c_o_o_l_i_n_g_f_a_n",
    "COOLER FAN": "cooler_fan_grill_jalli",
    "CAPACITOR": "c_a_p_a_c_i_t_o_r_s",
    "CANOPY": "fan_canopy",
    "TELEPHONE": "telephone_products_accessories",
    "TRFLON PLUMBER": "trflon_plumber_tape",
    "PVC HEATSEALING": "pvc_heatsealing",
    "STEELGRIP": "pvc_adhesive_wonder_steelgrip_tape",
    "FIBREGLASS UNVARNISHED": "fibreglass_unvarnished_tape",
    "WEBBING COTTON": "webbing_cotton_tape",
    "SUBMERSIBLE TAPE": "rubber_submersible_tape",
    "TEFLON TAPE ADHESIVE": "teflon_tape_adhesive",
    "TEFLON TAPE": "teflon_tape",
    "COTTON TAPE LOTUS": "cotton_tape_lotus",
    "SUPERFINE COTTON TAPE": "superfine_cotton_tape",
    "SEALER": "pvc_sealer_automatic_machine_parts",
    "BATTERY": "battery_accessories",
    "CUTTER": "taparia_tools",
    "PLIER": "taparia_tools",
    "SCREW DRIVER": "taparia_tools",
    "TESTER": "taparia_tools",
    "ALLEN KEY": "taparia_tools",
    "HACKSAW": "taparia_tools",
    "CRIMPING": "taparia_tools",
    "FERRULES": "taparia_tools",
    "KUNDIP": "kundip_items",
    "TARA / DHARIA": "tara_dharia_items",
    "SOLDRON": "soldron_items",
    "MALA": "soldron_items",
    "TONI": "soldron_items",
    "SOLDER STICK": "soldron_items",
    "SOLDER WIRE": "soldron_items",
    "SOLDERING PASTE": "soldron_items",
    "SOLDER POT": "soldron_items",
    "HEAT SINK": "soldron_items",
    "PULLER": "taparia_tools",
    "CABLE TIE": "nylon_cable_tie",
    "A TO Z": "taparia_tools",
    "BULB": "battery_accessories",
    "FUSE": "tinned_copper_fuse_wire",
    "PUSH BUTTON": "ax_items",
    "ROCKER SWITCH": "ax_items",
    "TOGGLE SWITCH": "ax_items",
    "P CLIP": "pvc_p_clip",
    "CERAMIC": "kundip_items"
}

def get_image(cat, item_name):
    text = (cat + " " + item_name).upper()
    for k, v in IMG_KEYWORDS.items():
        if k in text:
            return v
    return ""

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

# Sort by sr_no exactly
rows.sort(key=lambda x: int(x['sr_no']) if x['sr_no'].isdigit() else 99999)

current_cat = "General Items"

for row in rows:
    item_name = row['item_name']
    
    # Check if item name is essentially just a size (e.g. "2mm", "1/2 inch")
    # or if we are in "General Items" and need to find a new category
    if row['category'] == 'General Items':
        # If the item_name is long and has letters, it might be a new category header
        if len(item_name) > 5 and not re.match(r'^[\d\.\/\s]+[a-zA-Z]*$', item_name):
            # Extract size if it's at the end
            m = re.search(r'^(.*?)\s+([\d\.\/]+[a-zA-Z]*)$', item_name)
            if m:
                current_cat = m.group(1).strip()
                row['item_name'] = m.group(2).strip()
                row['size'] = m.group(2).strip()
            else:
                current_cat = item_name
                
    elif row['category']:
        current_cat = clean_cat(row['category'])
        
    row['category'] = current_cat
    
    # If item_name is empty or just matches category, fix it
    if not row['item_name'] or row['item_name'] == current_cat:
        if row['size']:
            row['item_name'] = row['size']
        else:
            row['item_name'] = current_cat
            
    # Fix images
    if not row['image_ref'] or row['image_ref'].startswith('item_'):
        # Keep inline images if they exist, else fallback
        if not row['image_ref']:
            row['image_ref'] = get_image(row['category'], row['item_name'])
    else:
        row['image_ref'] = get_image(row['category'], row['item_name'])

# Write back
with open('data/catalog_data_fixed.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("Fixed categories and images!")
