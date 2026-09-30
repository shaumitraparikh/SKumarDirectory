import os
from pathlib import Path
import csv
import re

os.chdir(Path(__file__).resolve().parents[2])

# Precise mapping of category strings to available group image files
IMG_MAP = {
    "ART SILK TUBE / Sleeves": "art_silk_tube_sleeves",
    "FIBREGLASS B CLASS YELLOW TUBE": "fibreglass_b_class_yellow_tube",
    "FIBREGLASS B CLASS WHITE SPECIAL TUBE": "fibreglass_b_class_white_special_tube",
    "FIBREGLASS F CLASS TUBE": "fibreglass_f_class_tube",
    "FIBREGLASS PVC COATED CHINA TUBE": "fibreglass_pvc_coated_china_tube",
    "FIBREGLASS SILICON H CLASS CHINA TUBE": "fibreglass_silicon_h_class_china_tube",
    "PVC CORD AND PIPES": "pvc_pipes",
    "P.V.C. HEAT SHINKABLE TUBE": "p_v_c_heat_shinkable_tube",
    "Rubber Type Heat Shrinkable Tubing": "p_v_c_heat_shinkable_tube",
    "SILICON RUBBER TEFLON TUBE": "silicon_rubber_teflon_tube",
    "TEFLON TUBE": "teflon_tube",
    "PVC Flexible Pipe": "pvc_flexible_pipe",
    "PVC Flexible Pipe Adaptor": "pvc_flexible_pipe_adaptor",
    "Galvanised Flexible Pipe": "pvc_flexible_pipe",
    "M a r k i n g P r i n t i n g S l e v e / T u b i n g": "m_a_r_k_i_n_g_p_r_i_n_t_i_n_g",
    "PE SPIRAL WRAPPING TUBE": "pe_spiral_wrapping_tube",
    "PVC Channel Box": "pvc_channel_box",
    "Fiber Glass Varnished Cable": "fiber_glass_varnished_cable",
    "TEFLON CABLE": "teflon_cable",
    "Tinned Copper Fuse Wire": "tinned_copper_fuse_wire",
    "Insulating Varnish": "insulating_varnish",
    "C o o l i n g F a n": "c_o_o_l_i_n_g_f_a_n",
    "Cooler Fan Grill / Jalli": "cooler_fan_grill_jalli",
    "C A P A C I T O R S": "c_a_p_a_c_i_t_o_r_s",
    "FAN CANOPY": "fan_canopy",
    "Telephone Products & Accessories": "telephone_products_accessories",
    "TRFLON PLUMBER TAPE": "trflon_plumber_tape",
    "PVC HEATSEALING NON ADHESIVE TAPE": "pvc_heatsealing",
    "PVC ADHESIVE WONDER STEELGRIP TAPE": "pvc_adhesive_wonder_steelgrip_tape",
    "FIBREGLASS UNVARNISHED TAPE": "fibreglass_unvarnished_tape",
    "WEBBING COTTON TAPE": "webbing_cotton_tape",
    "Rubber Submersible Tape": "rubber_submersible_tape",
    "TEFLON TAPE ADHESIVE": "teflon_tape_adhesive",
    "TEFLON TAPE NON-ADHESIVE": "teflon_tape",
    "COTTON TAPE LOTUS": "cotton_tape_lotus",
    "SUPERFINE COTTON TAPE": "superfine_cotton_tape",
    "PVC Sealer Automatic Machine & Parts": "pvc_sealer_automatic_machine_parts",
    "P V C , COTTON CORDS": "pvc_cord",
}

with open('data/catalog_data.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

for row in rows:
    cat = row['category'].strip()
    img = row['image_ref'].strip()
    
    # If the image is an inline image from the docx, KEEP IT!
    if img.startswith('item_'):
        continue
        
    # Otherwise, ONLY assign if there's a perfect match in our map
    new_img = ""
    for map_cat, map_file in IMG_MAP.items():
        if map_cat.lower() == cat.lower():
            new_img = map_file
            break
            
    # Also handle some loose string matches for exact items if needed, but very carefully
    # We will just strictly rely on the category name matching the map.
    row['image_ref'] = new_img

with open('data/catalog_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("Images remapped accurately!")
