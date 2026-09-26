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

The search catalog's proforma bill calculates CGST and SGST separately at 9%
each by default (18% total). Both rates can be adjusted in the cart; tax is
calculated on the taxable subtotal after item discounts.
The print catalog starts with the source price-list business and sales-contact
header. Product dimensions such as base-bar L/F size and Teflon ID/OD sizes are
stored and shown as distinct specifications.

## GitHub Pages

Pushing to `main` automatically builds and deploys both catalogs to GitHub Pages.
The repository landing page links to the searchable and print-ready catalogs.
On Windows, `1_Click_Update.bat` rebuilds both HTML files and commits the catalog
builder, templates, data, configuration, image-folder changes, and generated
HTML files, then automatically pushes the catalog commit to `origin/main` to
start the Pages deployment. No confirmation prompt is required. Run it from a
cleanly synchronized checkout on the `main` branch with Git credentials
configured for fetching and pushing. The updater stops without building or
committing if local `main` is not exactly at `origin/main`; synchronize the
branch first rather than risking a push of unrelated commits.

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
├── 1_Click_Update.bat            <- Rebuild, commit, and automatically push
├── build_catalog.py              <- Catalog generator used by local and Pages builds
├── config.json                   <- Company info & settings
├── maintenance scripts (*.py)    <- Data/image audit and repair utilities
└── README.md                     <- This file
```

## How to Update Prices / Add Items

1. Open `data/catalog_data.csv` in Excel
2. Edit prices, add new rows with the next serial number, or update item names
3. Save the CSV file
4. Run `1_Click_Update.bat` from the repository's `main` checkout to rebuild and
   commit and push the source and generated catalogs
5. Wait for the success message; GitHub Actions then deploys both pages
6. Open the generated HTML files locally or wait for the Pages workflow to
   finish before refreshing the live pages

The numbered product serials must remain unique and sequential. The updater
includes the builder and templates as well as the CSV and generated HTML so a
Pages build uses the same catalog data and layout as the local build. A run with
no catalog changes creates no empty commit or unnecessary push.

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
