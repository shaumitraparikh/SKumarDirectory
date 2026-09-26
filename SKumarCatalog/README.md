# GSC / S. Kumar Catalog Management System

**General Supply Corporation / S. Kumar & Bros.**
Price List & Product Catalog Generator

## Quick Start

```bash
# Generate catalogs (run this whenever you update the CSV)
python build_catalog.py
```

This creates two files in `output/`:
- **print_catalog.html** - Print-ready catalog (Ctrl+P in browser -> Save as PDF)
- **search_catalog.html** - Searchable web catalog with filters

## GitHub Pages

Pushing to `main` automatically builds and deploys both catalogs to GitHub Pages.
The repository landing page links to the searchable and print-ready catalogs.
On Windows, `1_Click_Update.bat` rebuilds both HTML files, commits the catalog
data, configuration, image-folder changes, and generated HTML files, then pushes
to `origin/main` to start the deployment. Run it from a checkout on the `main`
branch with Git credentials configured for pushing to the repository.

## Folder Structure

```
SKumarCatalog/
├── data/
│   └── catalog_data.csv          <- EDIT THIS in Excel
├── images/                       <- Product images
│   ├── photo_image1.png
│   ├── list_image1.png
│   └── ...
├── templates/
│   ├── print_template.html       <- Print catalog template
│   └── search_template.html      <- Search catalog template
├── output/
│   ├── print_catalog.html        <- GENERATED print catalog
│   └── search_catalog.html       <- GENERATED search catalog
├── build_catalog.py              <- Run this to generate catalogs
├── extract_from_docx.py          <- Extract data from .docx files
├── config.json                   <- Company info & settings
└── README.md                     <- This file
```

## How to Update Prices / Add Items

1. Open `data/catalog_data.csv` in Excel
2. Edit prices, add new rows, update item names
3. Save the CSV file
4. Run: `python build_catalog.py`
5. Open the HTML files in a browser to view

## CSV Columns

| Column | Description | Example |
|--------|-------------|---------|
| sr_no | Serial number | 138 |
| category | Product category/group | PVC Flexible Pipe |
| item_name | Full item description | PVC Flexible Pipe I.D. 10mm |
| size | Size specification | 10mm |
| hsn_code | HSN tax code | 39173100 |
| list_price | Price | 660.00 |
| unit | Unit of measurement | Coil, Mtr., Pcs., Roll |
| packing | Packing info | 100mtr.Coil |
| id_size | Inner diameter | 10mm |
| od_size | Outer diameter | 12mm |
| lf_size | Lay-flat size | 15mm |
| image_ref | Image filename (no extension) | pvc_flexible_pipe |
| page | Page number for print | 2 |
| notes | Special notes | |

## Adding New Products from a .docx File

```bash
python extract_from_docx.py [path_to_docx_folder]
```

This extracts data and images from the Word documents.

## Requirements

- Python 3.x
- python-docx (`pip install python-docx`) - only for extraction
- Pillow (`pip install Pillow`) - only for extraction  
- jinja2 (`pip install jinja2`) - for building catalogs

## Company Info

Edit `config.json` to update company name, phone, address, date, etc.
