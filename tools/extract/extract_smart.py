import csv
import re
from docx import Document
from collections import OrderedDict
from pathlib import Path

CATEGORY_IMAGE_MAP = {
    "ART SILK TUBE / Sleeves": "art_silk_tube_sleeves",
    "FIBREGLASS B CLASS YELLOW TUBE": "fibreglass_b_class_yellow_tube",
    "FIBREGLASS B CLASS WHITE SPECIAL TUBE": "fibreglass_b_class_white_special_tube",
    "FIBREGLASS F CLASS TUBE": "fibreglass_f_class_tube",
    "FIBREGLASS PVC COATED CHINA TUBE": "fibreglass_pvc_coated_china_tube",
    "FIBREGLASS SILICON H CLASS CHINA TUBE": "fibreglass_silicon_h_class_china_tube",
    "PVC CORD": "pvc_cord",
    "PVC PIPES": "pvc_pipes",
    "P.V.C. HEAT SHINKABLE TUBE": "p_v_c_heat_shinkable_tube",
    "SILICON RUBBER TEFLON TUBE": "silicon_rubber_teflon_tube",
    "TEFLON TUBE": "teflon_tube",
    "PVC Flexible Pipe": "pvc_flexible_pipe",
    "PVC Flexible Pipe Adaptor": "pvc_flexible_pipe_adaptor",
    "Galvanished G.I. Flexible Pipe": "galvanished_g_i_flexible_pipe",
    "Rubber Type HeatShrinkable  Tubing Available in All Colour": "rubber_type_heatshrinkable_tubing_available_in_all_colour",
    "M a r k i n g    P r i n t i n g   ": "m_a_r_k_i_n_g_p_r_i_n_t_i_n_g",
    "PE SPIRAL WRAPPING TUBE": "pe_spiral_wrapping_tube",
    "PVC Channel Box": "pvc_channel_box",
    "Fiber Glass Varnished Cable": "fiber_glass_varnished_cable",
    "TEFLON   CABLE": "teflon_cable",
    "Tinned Copper Fuse Wire": "tinned_copper_fuse_wire",
    "Insulating Varnish": "insulating_varnish",
    "C o o l i  n g     F a n": "c_o_o_l_i_n_g_f_a_n",
    "Cooler  Fan  Grill / Jalli": "cooler_fan_grill_jalli",
    "C A P A C I T O R S": "c_a_p_a_c_i_t_o_r_s",
    "FAN  CANOPY": "fan_canopy",
    "Telephone  Products & Accessories": "telephone_products_accessories",
    "TRFLON PLUMBER TAPE": "trflon_plumber_tape",
    "PVC HEATSEALING ": "pvc_heatsealing",
    "PVC ADHESIVE WONDER STEELGRIP TAPE": "pvc_adhesive_wonder_steelgrip_tape",
    "FIBREGLASS UNVARNISHED TAPE": "fibreglass_unvarnished_tape",
    "WEBBING COTTON TAPE": "webbing_cotton_tape",
    "Rubber Submersible Tape": "rubber_submersible_tape",
    "TEFLON  TAPE  ADHESIVE": "teflon_tape_adhesive",
    "TEFLON  TAPE  ": "teflon_tape",
    "COTTON TAPE LOTUS": "cotton_tape_lotus",
    "SUPERFINE COTTON TAPE": "superfine_cotton_tape",
    "PVC SEALER AUTOMATIC MACHINE & PARTS": "pvc_sealer_automatic_machine_parts",
    # Add some robust fallback matches
    "ART SILK": "art_silk_tube_sleeves",
    "YELLOW TUBE": "fibreglass_b_class_yellow_tube",
    "WHITE SPECIAL TUBE": "fibreglass_b_class_white_special_tube",
    "CHINA TUBE": "fibreglass_pvc_coated_china_tube",
    "PVC CORD": "pvc_cord",
    "P.V.C. HEAT SHRINKABLE": "p_v_c_heat_shinkable_tube",
    "SILICON RUBBER": "silicon_rubber_teflon_tube",
    "TEFLON TUBE": "teflon_tube",
    "FLEXIBLE PIPE": "pvc_flexible_pipe",
    "ADAPTOR": "pvc_flexible_pipe_adaptor",
    "GALVANISHED": "galvanished_g_i_flexible_pipe",
    "PE SPIRAL": "pe_spiral_wrapping_tube",
    "CHANNEL BOX": "pvc_channel_box",
    "VARNISHED CABLE": "fiber_glass_varnished_cable",
    "TEFLON CABLE": "teflon_cable",
    "COPPER FUSE WIRE": "tinned_copper_fuse_wire",
    "VARNISH": "insulating_varnish",
    "CAPACITOR": "c_a_p_a_c_i_t_o_r_s",
    "COOLING FAN": "c_o_o_l_i_n_g_f_a_n",
    "COOLER FAN": "cooler_fan_grill_jalli",
    "TELEPHONE": "telephone_products_accessories",
    "SEALER": "pvc_sealer_automatic_machine_parts",
    "BATTERY": "battery_accessories", # Custom mapping, might not exist as photo but ensures fallback
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
    "SOLDER": "soldron_items",
    "DESOLDERING": "soldron_items",
    "TIN/LEAD": "solder_stick",
    "CABLE TIE": "nylon_cable_tie",
    "P CLIP": "pvc_p_clip",
    "AX ITEMS": "ax_items",
    "CAMERA": "ax_items",
    "REGULATOR": "ax_items",
}

def get_image_ref(category, particulars):
    text = f"{category} {particulars}".upper()
    best_match = ""
    for k, v in CATEGORY_IMAGE_MAP.items():
        if k.upper() in text:
            best_match = v
            # Keep looking for a longer match
    return best_match

def clean_text(text):
    if not text: return ""
    text = text.replace('\u00b6', '').replace('\u00a0', ' ')
    text = text.replace('â€œ', '"').replace('â€\x9d', '"').replace('â€˜', "'").replace('â€™', "'")
    text = text.replace('ô', '"').replace('ö', '"').replace('æ', "'")
    return re.sub(r'\s+', ' ', text).strip()

def extract_hsn(text):
    m = re.search(r'HSN\s*(?:Code)?\s*[-:]?\s*(\d{4,8})', text, re.IGNORECASE)
    if m:
        hsn = m.group(1)
        rem = re.sub(r'HSN\s*(?:Code)?\s*[-:]?\s*\d{4,8}', '', text, flags=re.IGNORECASE).strip()
        return hsn, rem
    return None, text

def parse_price(text):
    cleaned = re.sub(r'[^\d.\-]', '', text)
    if cleaned:
        try:
            return f"{float(cleaned):.2f}"
        except:
            pass
    return text.strip()

class TableParser:
    def __init__(self, doc_path):
        self.doc = Document(doc_path)
        self.items = []
        self.cat_left = ""
        self.cat_right = ""
        self.hsn_left = ""
        self.hsn_right = ""
        self.pack_left = ""
        self.pack_right = ""

    def process(self):
        for ti, table in enumerate(self.doc.tables):
            nc = len(table.columns)
            if nc < 5: continue
            
            # Find data rows
            start_idx = -1
            for ri, row in enumerate(table.rows[:10]):
                cells = [clean_text(c.text) for c in row.cells]
                if any('Sr.No' in c for c in cells):
                    start_idx = ri + 1
                    break
            
            if start_idx == -1: continue
            
            for ri in range(start_idx, len(table.rows)):
                cells = [clean_text(c.text) for c in table.rows[ri].cells]
                if not any(c and c not in (',,', 'ÆÆ') for c in cells):
                    continue
                
                self.parse_row(ti, nc, cells)

    def add_item(self, ti, sr, cat, part, size, hsn, list_price, per, packing):
        if not sr or not sr.replace('.', '').isdigit():
            return
            
        sr = sr.replace('.', '')
        hsn_found, part = extract_hsn(part)
        if hsn_found: hsn = hsn_found
        
        hsn_found_size, size = extract_hsn(size)
        if hsn_found_size: hsn = hsn_found_size
        
        # Clean bad category strings
        if cat in (',,', 'ÆÆ', '', '100Pcs.', '100pc Pkt', 'Pcs.'):
            cat = "General Items"
            
        # Clean Per
        per = per.replace('ÆÆ', '').replace(',,', '').strip()
        if not per and cat in ('General Items', 'Uncategorized'): return
        
        # deduplicate names
        item_name = part if part and len(part) > 1 and part not in (',,', 'ÆÆ') else cat
        if size and size not in item_name:
            if item_name != cat:
                item_name = f"{item_name} {size}"
            else:
                item_name = f"{cat} {size}"
                
        if not item_name.strip():
            item_name = f"{cat} {size}"

        self.items.append({
            'sr_no': sr,
            'category': cat.strip(),
            'item_name': item_name.strip(),
            'size': size.strip(),
            'hsn_code': hsn.strip(),
            'list_price': parse_price(list_price),
            'unit': per,
            'packing': packing.strip(),
            'image_ref': get_image_ref(cat, part),
            'page': str(ti+1)
        })

    def parse_row(self, ti, nc, cells):
        # Table specific parsers based on columns
        if ti == 0 and nc == 12:
            # Left: 0(Sr), 1(Part), 2(Size), 3(List), 4(Per)
            sr = cells[0]
            part = " ".join(list(dict.fromkeys([c for c in cells[1:3] if c and c not in (",,", "ÆÆ")])))
            size = cells[2]
            price = cells[3]
            per = cells[4]
            
            if part and not price and not sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                if p and len(p) > 3 and p not in (',,', 'ÆÆ'): self.cat_left = p
            elif sr:
                if part and not price and len(part) > 5 and part not in (',,', 'ÆÆ') and not __import__('re').match(r'^\d+(\.\d+)?\s*[a-zA-Z"]*$', part):
                    if part and len(part)>3 and part not in (",,", "ÆÆ"): self.cat_left = part
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                self.add_item(ti, sr, self.cat_left, p, size, self.hsn_left, price, per, "")

            # Right: 5(Sr), 6(Part), 8(Size), 10(List), 11(Per)
            sr_r = cells[5]
            part_r = " ".join(list(dict.fromkeys([c for c in cells[6:8] if c and c not in (",,", "ÆÆ")])))
            size_r = cells[8]
            price_r = cells[10]
            per_r = cells[11]
            
            if part_r and not price_r and not sr_r:
                h, p = extract_hsn(part_r)
                if h: self.hsn_right = h
                if p and len(p) > 3 and p not in (',,', 'ÆÆ'): self.cat_right = p
            elif sr_r:
                if part_r and not price_r and len(part_r) > 5 and part_r not in (',,', 'ÆÆ') and not __import__('re').match(r'^\d+(\.\d+)?\s*[a-zA-Z"]*$', part_r):
                    if part_r and len(part_r)>3 and part_r not in (",,", "ÆÆ"): self.cat_right = part_r
                h, p = extract_hsn(part_r)
                if h: self.hsn_right = h
                self.add_item(ti, sr_r, self.cat_right, p, size_r, self.hsn_right, price_r, per_r, "")

        elif ti == 1 and nc == 15:
            # Left: 0,1,2(Pack),3,4
            sr = cells[0]
            part = " ".join(list(dict.fromkeys([c for c in cells[1:3] if c and c not in (",,", "ÆÆ")])))
            pack = cells[2]
            price = cells[3]
            per = cells[4]
            if part and not sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                if p and len(p)>3 and p not in (",,", "ÆÆ"): self.cat_left = p
            elif sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                self.add_item(ti, sr, self.cat_left, p, "", self.hsn_left, price, per, pack)

            # Right: 5,6,11(Pack),13,14
            sr_r = cells[5]
            part_r = " ".join(list(dict.fromkeys([c for c in cells[6:8] if c and c not in (",,", "ÆÆ")])))
            pack_r = cells[11]
            price_r = cells[13]
            per_r = cells[14]
            if part_r and not sr_r:
                h, p = extract_hsn(part_r)
                if h: self.hsn_right = h
                if p and len(p)>3 and p not in (",,", "ÆÆ"): self.cat_right = p
            elif sr_r:
                h, p = extract_hsn(part_r)
                if h: self.hsn_right = h
                self.add_item(ti, sr_r, self.cat_right, p, "", self.hsn_right, price_r, per_r, pack_r)

        elif ti == 2 and nc == 9:
            # Left: 0,1,2,3
            sr = cells[0]
            part = " ".join(list(dict.fromkeys([c for c in cells[1:3] if c and c not in (",,", "ÆÆ")])))
            price = cells[2]
            per = cells[3]
            if part and not sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                if p and len(p)>3 and p not in (",,", "ÆÆ"): self.cat_left = p
            elif sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                self.add_item(ti, sr, self.cat_left, p, "", self.hsn_left, price, per, "")

            # Right: 4,5,6(HSN),7,8
            sr_r = cells[4]
            part_r = cells[5]
            hsn_r = cells[6]
            price_r = cells[7]
            per_r = cells[8]
            if part_r and not sr_r:
                if part_r and len(part_r)>3 and part_r not in (",,", "ÆÆ"): self.cat_right = part_r
            elif sr_r:
                if hsn_r: self.hsn_right = hsn_r
                self.add_item(ti, sr_r, self.cat_right, part_r, "", self.hsn_right, price_r, per_r, "")

        elif ti == 3 and nc == 11:
            # Left: 0,1,4,5
            sr = cells[0]
            part = " ".join(list(dict.fromkeys([c for c in cells[1:3] if c and c not in (",,", "ÆÆ")])))
            price = cells[4]
            per = cells[5]
            if part and not sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                if p and len(p)>3 and p not in (",,", "ÆÆ"): self.cat_left = p
            elif sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                self.add_item(ti, sr, self.cat_left, p, "", self.hsn_left, price, per, "")

            # Right: 6,7,8(HSN),9,10
            sr_r = cells[6]
            part_r = cells[7]
            hsn_r = cells[8]
            price_r = cells[9]
            per_r = cells[10]
            if part_r and not sr_r:
                if part_r and len(part_r)>3 and part_r not in (",,", "ÆÆ"): self.cat_right = part_r
            elif sr_r:
                if hsn_r: self.hsn_right = hsn_r
                self.add_item(ti, sr_r, self.cat_right, part_r, "", self.hsn_right, price_r, per_r, "")

        elif ti == 4 and nc == 7:
            # Single: 0,2,3,4(HSN),5,6
            sr = cells[0]
            itemno = cells[2]
            part = cells[3]
            hsn = cells[4]
            price = cells[5]
            per = cells[6]
            if part and not sr:
                if part and len(part)>3 and part not in (",,", "ÆÆ"): self.cat_left = part
            elif sr:
                if hsn: self.hsn_left = hsn
                p = f"{itemno} {part}" if itemno else part
                self.add_item(ti, sr, "Kundip Items", p, "", self.hsn_left, price, per, "")

        elif ti == 5 and nc == 13:
            # Left: 0,1,2,3
            sr = cells[0]
            part = " ".join(list(dict.fromkeys([c for c in cells[1:3] if c and c not in (",,", "ÆÆ")])))
            price = cells[2]
            per = cells[3]
            if part and not sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                if p and len(p)>3 and p not in (",,", "ÆÆ"): self.cat_left = p
            elif sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                self.add_item(ti, sr, self.cat_left, p, "", self.hsn_left, price, per, "")

            # Right: 4,5,10(HSN),11,12
            sr_r = cells[4]
            part_r = " ".join(list(dict.fromkeys([c for c in cells[5:10] if c and c not in (",,", "ÆÆ")])))
            hsn_r = cells[10]
            price_r = cells[11]
            per_r = cells[12]
            if part_r and not sr_r:
                if part_r and len(part_r)>3 and part_r not in (",,", "ÆÆ"): self.cat_right = part_r
            elif sr_r:
                if hsn_r: self.hsn_right = hsn_r
                self.add_item(ti, sr_r, self.cat_right, part_r, "", self.hsn_right, price_r, per_r, "")

        elif ti == 6 and nc == 8:
            # Left: 0,1,2,3
            sr = cells[0]
            part = " ".join(list(dict.fromkeys([c for c in cells[1:3] if c and c not in (",,", "ÆÆ")])))
            price = cells[2]
            per = cells[3]
            if part and not sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                if p and len(p)>3 and p not in (",,", "ÆÆ"): self.cat_left = p
            elif sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                self.add_item(ti, sr, self.cat_left, p, "", self.hsn_left, price, per, "")

            # Right: 4,5,6,7
            sr_r = cells[4]
            part_r = cells[5]
            price_r = cells[6]
            per_r = cells[7]
            if part_r and not sr_r:
                h, p = extract_hsn(part_r)
                if h: self.hsn_right = h
                if p and len(p)>3 and p not in (",,", "ÆÆ"): self.cat_right = p
            elif sr_r:
                h, p = extract_hsn(part_r)
                if h: self.hsn_right = h
                self.add_item(ti, sr_r, self.cat_right, p, "", self.hsn_right, price_r, per_r, "")

        elif (ti == 7 or ti == 8) and nc == 12:
            # Left: 0,1,2(Size),3,4
            sr = cells[0]
            part = " ".join(list(dict.fromkeys([c for c in cells[1:3] if c and c not in (",,", "ÆÆ")])))
            size = cells[2]
            price = cells[3]
            per = cells[4]
            if part and not sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                if p and len(p)>3 and p not in (",,", "ÆÆ"): self.cat_left = p
            elif sr:
                h, p = extract_hsn(part)
                if h: self.hsn_left = h
                self.add_item(ti, sr, self.cat_left, p, size, self.hsn_left, price, per, "")

            # Right: 5,6,8(Size),10,11
            sr_r = cells[5]
            part_r = " ".join(list(dict.fromkeys([c for c in cells[6:8] if c and c not in (",,", "ÆÆ")])))
            size_r = cells[8]
            price_r = cells[10]
            per_r = cells[11]
            if part_r and not sr_r:
                h, p = extract_hsn(part_r)
                if h: self.hsn_right = h
                if p and len(p)>3 and p not in (",,", "ÆÆ"): self.cat_right = p
            elif sr_r:
                h, p = extract_hsn(part_r)
                if h: self.hsn_right = h
                self.add_item(ti, sr_r, self.cat_right, p, size_r, self.hsn_right, price_r, per_r, "")

        elif ti in (9, 12) and nc == 10:
            # Left: 0,1,2(HSN),3,4
            sr = cells[0]
            part = " ".join(list(dict.fromkeys([c for c in cells[1:3] if c and c not in (",,", "ÆÆ")])))
            hsn = cells[2]
            price = cells[3]
            per = cells[4]
            if part and not sr:
                if part and len(part)>3 and part not in (",,", "ÆÆ"): self.cat_left = part
            elif sr:
                if hsn: self.hsn_left = hsn
                self.add_item(ti, sr, self.cat_left, part, "", self.hsn_left, price, per, "")

            # Right: 5,6,7(HSN),8,9
            sr_r = cells[5]
            part_r = " ".join(list(dict.fromkeys([c for c in cells[6:8] if c and c not in (",,", "ÆÆ")])))
            hsn_r = cells[7]
            price_r = cells[8]
            per_r = cells[9]
            if part_r and not sr_r:
                if part_r and len(part_r)>3 and part_r not in (",,", "ÆÆ"): self.cat_right = part_r
            elif sr_r:
                if hsn_r: self.hsn_right = hsn_r
                self.add_item(ti, sr_r, self.cat_right, part_r, "", self.hsn_right, price_r, per_r, "")


if __name__ == "__main__":
    repo_dir = Path(__file__).resolve().parents[2]
    doc_path = repo_dir / "List 2025.docx"
    parser = TableParser(doc_path)
    parser.process()
    
    # Save to CSV
    out_path = repo_dir / "data" / "catalog_data.csv"
    fieldnames = ['sr_no', 'category', 'item_name', 'size', 'hsn_code', 'list_price', 'unit', 'packing', 'image_ref', 'page']
    
    with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for item in sorted(parser.items, key=lambda x: int(x['sr_no']) if x['sr_no'].isdigit() else 9999):
            writer.writerow(item)
    
    print(f"Extraction complete! Extracted {len(parser.items)} items.")
