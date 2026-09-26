import csv

IMG_MAP = {
    "yellow": "fibreglass_b_class_yellow_tube",
    "white special": "fibreglass_b_class_white_special_tube",
    "f class tube": "fibreglass_f_class_tube",
    "china tube": "fibreglass_pvc_coated_china_tube",
    "cord and pipes": "pvc_pipes",
    "teflon tube": "teflon_tube",
    "galvanised": "pvc_flexible_pipe",
    "adaptor": "pvc_flexible_pipe_adaptor",
    "shrinkable": "p_v_c_heat_shinkable_tube",
    "m a r k i n g": "m_a_r_k_i_n_g_p_r_i_n_t_i_n_g",
    "channel box": "pvc_channel_box",
    "teflon cable": "teflon_cable",
    "telephone": "telephone_products_accessories",
    "sealer": "pvc_sealer_automatic_machine_parts",
    "fuse wire": "tinned_copper_fuse_wire",
    "glass & ceramics fuses": "tinned_copper_fuse_wire",
    "cotton cords": "pvc_cord",
    "rocker switch": "tinned_copper_fuse_wire", # Wait, why rocker switch? No, remove.
}

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

for row in rows:
    if row['image_ref'].startswith('item_'): continue
    cat_lower = row['category'].lower()
    
    # Clean broken mappings
    if row['image_ref'] in ['tinned_copper_fuse_wire'] and "fuse" not in cat_lower:
        row['image_ref'] = ""
    if row['image_ref'] in ['pvc_cord'] and "cord" not in cat_lower:
        row['image_ref'] = ""
        
    for k, v in IMG_MAP.items():
        if k in cat_lower and "fuse" not in k and "cord" not in k: # just safe mapping
            row['image_ref'] = v
            break
            
    # explicit overrides
    if "yellow" in cat_lower: row['image_ref'] = "fibreglass_b_class_yellow_tube"
    if "white special" in cat_lower: row['image_ref'] = "fibreglass_b_class_white_special_tube"
    if "f class" in cat_lower: row['image_ref'] = "fibreglass_f_class_tube"
    if "china tube" in cat_lower and "silicon" not in cat_lower: row['image_ref'] = "fibreglass_pvc_coated_china_tube"
    if "china tube" in cat_lower and "silicon" in cat_lower: row['image_ref'] = "fibreglass_silicon_h_class_china_tube"
    if "cord and pipe" in cat_lower: row['image_ref'] = "pvc_pipes"
    if "cotton cord" in cat_lower: row['image_ref'] = "pvc_cord"
    if "glass & ceramics fuses" in cat_lower: row['image_ref'] = "tinned_copper_fuse_wire"

with open('data/catalog_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("Images fixed!")
