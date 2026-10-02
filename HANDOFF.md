# S. Kumar & Bros - Catalog & POS System Handoff Document

This document summarizes the architecture, configuration, and current state of the S. Kumar & Bros catalog application. Keep it for future reference or if you need to hand off development to another team.

## Overview
This application serves as both a public-facing product catalog (for static hosting on GitHub Pages) and a powerful local Point of Sale (POS) & Billing system (for your local store use).

### Core Features
- **1,400+ Products**: Grouped into categories with ultra-fast search, filter, and sorting.
- **Cart & Order Flow**: Allows adding items to a cart, calculating item-level discounts, and applying IGST/CGST automatically.
- **Customer Directory**: Auto-fills customer details (Name, GSTIN, Phone, Address).
- **Proforma Invoices (Bills) & Estimates**: Supports generating proper Proforma Invoices or non-tax Estimates/Challans.
- **Local Persistence**: Saves all generated bills to your hard drive and exports them as DayBook Excel files for Tally.
- **Strictly Local Storage**: Sensitive customer data and internal bills are strictly `git ignored` to ensure absolute privacy when pushed to GitHub.

## Architecture

This is a **Data-First Static Application**. There is no heavy database like MySQL.

### 1. Data Layer (`data/`)
- `catalog_data.csv`: The source of truth for all 1,412 products and pricing.
- `client_data.csv`: Your customer directory. (Git ignored for privacy).
- `bills/YYYY-MM.csv`: Automatically generated monthly databases storing all your saved bills.
- `estimates/YYYY-MM.csv`: Automatically generated database for non-tax estimates/challans.
- `monthly_reports/`: Where your Tally-ready Excel DayBooks are generated.

### 2. Build Engine (`src/`)
- `src/build_catalog.py`: The heart of the system. This Python script reads your CSV data, parses the HTML templates in `app/templates/`, injects the data, and outputs the final flat HTML files.
- `src/seller/local_seller.py`: A lightweight background server that only runs on your local machine. It allows the web browser to save CSV files directly to your hard drive (bypassing browser security rules).
- `src/seller/export_tally.py`: Handles exporting the local monthly bills into Excel files formatted for Tally DayBook imports.
- `src/seller/prepare_tally_files.py`: The GST bridge. Splits saved bills per company, writes Tally-format `S-/G-DayBook.xlsx` + `HSNCodeSummary.xlsx` into the `TallyToOutputsForGST` checkout, then runs `process_data.py` to produce gst.gov.in JSON.

### 3. Frontend (`app/`)
- `app/templates/`: Jinja2 HTML templates used to build the pages (e.g. `search_template.html`).
- `app/assets/js/`: Vanilla JavaScript handling the cart, UI interactions, and virtual scrolling. No heavy frameworks like React are used to ensure maximum performance.
- `app/assets/css/`: Vanilla CSS stylesheets.

### 4. Output Pages (Root Directory)
- `index.html`: The main interactive POS and Search interface.
- `photo_catalog.html`: A highly visual, deduplicated photo gallery of categories.
- `print_catalog.html`: A compact, continuous 2-column list optimized for A4 printing.

## How to Run & Update

Everything has been consolidated into a single script for your convenience:

**Mac/Linux Command:**
```bash
./update.sh
```

**What `update.sh` does natively:**
1. Pulls the latest code from your team via GitHub.
2. Re-runs the Python builder (`src/build_catalog.py`) to generate fresh HTML from your data.
3. Runs the automated test suite to verify everything is safe.
4. Kills any old background server, and safely restarts the Local Seller API on port 8766.
5. Displays a clickable link to open your local browser to the Edit/POS interface.

(Note: `start.sh` and `stop.sh` have been completely removed, as `update.sh` now elegantly manages the background server lifecycle for you.)

## GST Filing Flow (POS -> Tally -> gst.gov.in)

Every saved bill is tagged with the company it was raised under, so both firms' GST
returns come out of one POS:

1. **Save a bill** in the POS. Pick the company with the **S. Kumar & Bros (S-)** /
   **GSC (G-)** radio before printing. The invoice number becomes `S-YYYYMM-NNNN`,
   `G-YYYYMM-NNNN`, or `EST-YYYYMM-NNNN` for non-tax estimates.
   Bills land in `data/bills/YYYY-MM.csv`; estimates in `data/estimates/YYYY-MM.csv`.
2. **Open Saved Bills** and press **🧾 Export & Prepare GST** (needs the local
   server from `update.sh`). This calls `POST /api/gst/prepare`.
3. The bridge writes, into `<TallyToOutputsForGST>/data/<org>/`:
   - `S-DayBook.xlsx` / `G-DayBook.xlsx` — 2 title rows, then the header row,
     with one `Sale Net <rate>% A/c.` + `CGST`/`SGST`/`IGST` column group per rate.
   - `HSN files/HSNCodeSummary.xlsx` — 3 title rows, then the header row.
4. `process_data.py` runs automatically and writes, per company:
   - `output/<org>/json/returns_MM_YYYY_<GSTIN>_offline.json` — upload this.
   - `output/<org>/xlsx/GSTReturn_MM_YYYY.xlsx` — review sheet.
   - `output/<org>/hsn/HSN_Summary_Sheet4.xlsx` — HSN table.

Notes:
- Estimates and 0%-rate bills are never filed as sales.
- Bills with **no buyer GSTIN** are written to the DayBook but skipped by the
  converter (they are B2C, not B2B invoices); the HSN summary still includes them.
- CLI equivalent: `python3 src/seller/prepare_tally_files.py --month 2026-10`.
  Add `--no-run` to write files without running the converter, or `--tally-repo`
  / `TALLY_REPO` if the checkout is not a sibling of this repository.

## Security & Access
- The Edit Mode, Cart, and Seller Tools are **hardcoded to be hidden** if the domain is not `localhost` or a local IP (like `192.168.x.x`). This guarantees that if a customer accesses the site on GitHub pages, they only see the catalog, not your billing software.
- The Git history has been scrubbed of old client data, ensuring nothing sensitive lives in the remote repository.

## GitHub Push Notice
Because the Git history was scrubbed to remove old client data, your local repository has diverged from GitHub's. The `main` branch on GitHub is also protected.
To successfully push any new changes, you must:
1. Temporarily disable the "Branch protection rules" for the `main` branch in your GitHub Repository Settings.
2. Run `git push --force origin main` from your terminal.
3. Re-enable branch protection.

## Test Suite
You can verify the health of the application at any time by running:
```bash
python3 -m unittest discover -s tests   # Python suites
for f in tests/*.test.js; do node "$f"; done   # Node suites
```
`./update.sh` runs both automatically. The suites cover category compilation,
item counts, billing math, cart interactions, the seller server, and the
POS -> Tally -> GST bridge.
