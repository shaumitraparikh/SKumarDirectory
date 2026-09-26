import os
import re
from pathlib import Path
from docx import Document
from PIL import Image
import io

def clean_filename(text):
    text = text.replace('\u00b6', '').replace('\u00a0', ' ')
    text = re.sub(r'[^A-Za-z0-9]+', '_', text)
    return text.lower().strip('_')

def extract_and_map_images():
    repo_dir = Path(__file__).resolve().parents[2]
    photo_doc_path = repo_dir / "docs 2025" / "GSC - SK Catlog Photo.docx"
    out_dir = repo_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    doc = Document(photo_doc_path)
    table = doc.tables[0]
    
    image_map = {}
    
    for ri in range(8, len(table.rows)):
        row = table.rows[ri]
        for ci, cell in enumerate(row.cells):
            text = cell.text.strip().split('\n')[0]
            if not text or len(text) < 3: continue
            
            blips = cell._element.xpath('.//a:blip')
            for blip in blips:
                embed_id = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                if not embed_id: continue
                
                try:
                    image_part = doc.part.related_parts[embed_id]
                    image_bytes = image_part.blob
                    
                    clean_name = clean_filename(text)
                    if clean_name in image_map:
                        clean_name = f"{clean_name}_{ri}_{ci}"
                        
                    ext = image_part.content_type.split('/')[-1]
                    if ext == 'x-emf': ext = 'png'
                    if ext == 'ms-photo' or ext == 'vnd.ms-photo': ext = 'wdp'
                    
                    out_path = out_dir / f"{clean_name}.{ext}"
                    with open(out_path, 'wb') as f:
                        f.write(image_bytes)
                        
                    # Convert WDP to PNG
                    if ext == 'wdp':
                        try:
                            # Pillow might not support WDP out of the box without plugins
                            # but let's just rename it or try to open
                            img = Image.open(out_path)
                            png_path = out_dir / f"{clean_name}.png"
                            img.save(png_path, "PNG")
                            os.remove(out_path)
                            ext = 'png'
                        except Exception as e:
                            print(f"Could not convert WDP to PNG: {e}")
                            
                    image_map[text] = clean_name
                    print(f"Saved {clean_name}.{ext} for label: {text}")
                except Exception as e:
                    print(f"Error extracting image at R{ri}C{ci}: {e}")
                    
    return image_map

if __name__ == "__main__":
    mapped = extract_and_map_images()
    print(f"\nExtracted and mapped {len(mapped)} images!")
