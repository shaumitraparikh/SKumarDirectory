# GSC / S. Kumar & Bros. — Product Catalog System

**General Supply Corporation / S. Kumar & Bros.**  
Digital Product Directory, Interactive POS/Ordering, Photo Catalog & Print Price List.

---

> ### 📌 TL;DR & Quick Instructions
>
> 🛒 **1. Find Products & Take Orders (`index.html`)**
> * **Browse**: Opens with **All Categories** showing the full catalog. Narrow with the category picker or search.
> * **Search**: Type any name, size, category, or HSN (e.g. `teflon 1mm`, `soldron 25w`, `hsn 3917`).
> * **Add Items**: Click **Add** (for priced items) or **Add to Quote** (enter custom quote rate directly in cart).
> * **Save / Print Bill**: Open the Cart → enter customer details → click **Save Proforma Bill** (select your `data` folder once to auto-save invoices) or **Print Current Bill**.
> * **WhatsApp**: Click **Send WhatsApp Order** to forward the formatted itemized order directly to sales.
>
> 🖼️ **2. Visual Photo Catalog (`photo_catalog.html`)**
> * Click category pill filters at the top or click any product photo to open a high-res lightbox preview.
>
> 📄 **3. Print Price List (`print_catalog.html`)**
> * Press **`Ctrl + P`** → Choose **Save as PDF** to export an up-to-date physical or digital price catalog.
>
> ✏️ **4. Update Prices or Products (Admin)**
> * Open **`data/catalog_data.csv`** in Excel → Edit prices or add items → Save → Double-click **`update.bat`**. It validates, rebuilds, and auto-pushes to GitHub Pages!

---

## ⚡ Quickstart

### 1. View & Use the Catalogs (Customers & Staff)
Double-click any of the standalone HTML files to open them in your browser, or visit the live GitHub Pages:
- **`index.html`** — 🛒 **Interactive POS & Search Catalog**: Real-time fuzzy search, category filters, interactive cart, WhatsApp order forwarding, and proforma bill generator.
- **`photo_catalog.html`** — 🖼️ **Visual Photo Catalog**: Browse products by category with high-resolution imagery and quick filters.
- **`print_catalog.html`** — 📄 **Print-Ready Price List**: Clean layout formatted for printing (`Ctrl + P` → Save as PDF).

### 2. Update Prices, Products, or Images (Admin)
1. Open **`data/catalog_data.csv`** in Microsoft Excel or Google Sheets.
2. Edit prices, adjust sizes/descriptions, or append new product rows.
3. Save the file and double-click **`update.bat`**.
   - Validates all serial numbers and prices.
   - Rebuilds all 3 catalog HTML pages.
   - Executes the automated test suite.
   - Automatically commits and pushes the updates to GitHub Pages!

---

## 📖 How to Use the System

### 🔍 1. Interactive Search & POS (`index.html`)
* **Landing View**: Shows the full catalog under **All Categories**. Use the category picker or search box to narrow results.
* **Fuzzy & Smart Search**: Matches prefixes, exact terms, and minor spelling typos.
* **Adding to Cart / Quote**:
  * For items with listed prices, click **Add** to add to cart.
  * For *Price on Request* items, click **Add to Quote**; you can enter custom quote rates directly inside the cart drawer.
* **Customer Directory**:
  * Copy `data/client_data.example.csv` to `data/client_data.csv` (git-ignored), then use **Load Customer List (CSV)** in checkout. Customer GSTINs are never published to GitHub Pages.
  * Type customer name/GSTIN in the checkout panel to auto-fill details once the CSV is loaded.
* **Proforma Invoice & Billing**:
  * Generates a branded proforma invoice with CGST/SGST tax breakdown, customer GSTIN, and company contact details.
  * Click **Save Proforma Bill**: On GitHub Pages / static hosting, the browser archives bills into `data/bills/` and `data/generated_bills/` via the File System Access API (or downloads a copy).
* **WhatsApp Order Handoff**:
  * Click **Send WhatsApp Order** to format the entire order into a structured WhatsApp message sent directly to the sales desk.

### 🖼️ 2. Visual Photo Catalog (`photo_catalog.html`)
* Filter quickly using the interactive top pill buttons (Tubes & Sleeves, Cables, Capacitors, Soldering, etc.).
* Click any product thumbnail to open a high-res lightbox preview with specifications.
* Use **Order from POS** links to open `index.html?category=...` with that category pre-selected.

### 📄 3. Print Catalog (`print_catalog.html`)
* Designed strictly for A4 printing and PDF export.
* Press `Ctrl + P`, set Margins to "Default", enable "Background graphics", and select **Save as PDF** to generate an up-to-date printed price sheet.

---

## 🏗️ 100% Static & Offline Architecture

This system is built as a **pure static web application**:
- **Zero Local Server Needed**: No Python background servers, daemons, or runtime dependencies required to run the catalogs.
- **Offline Ready**: Includes Service Worker caching (`app/sw.js`) and IndexedDB storage so catalogs and cart data work even without an internet connection.
- **Direct-to-Disk Archiving**: Uses the browser's native File System Access API to save customer orders directly into your local `data/` folder without needing a backend server.

---

## 📂 Project Structure

```
.
├── index.html                   <- Interactive search & POS catalog
├── photo_catalog.html           <- Visual photo catalog
├── print_catalog.html           <- Print-ready A4 price list
├── update.bat                   <- 1-Click build, test, and git publish script
├── Google_Review_QR.pdf         <- Google Review QR code asset
│
├── app/                         <- Website source files
│   ├── assets/
│   │   ├── css/                 <- Stylesheets (search_catalog.css, photo_catalog.css)
│   │   └── js/                  <- Front-end logic (commerce_core, search_catalog, etc.)
│   ├── templates/               <- Jinja2 HTML templates for building pages
│   └── sw.js                    <- Offline Service Worker cache engine
│
├── data/                        <- Databases and source documents
│   ├── catalog_data.csv         <- Canonical product database (edit this!)
│   ├── client_data.csv          <- Customer directory (git-ignored for privacy)
│   ├── client_data.example.csv  <- Template for customer directory CSV
│   ├── config.json              <- Company header, GSTIN, contacts, and tax rates
│   ├── bills/                   <- Generated monthly CSV bill registers (YYYY-MM.csv)
│   ├── generated_bills/         <- Archived HTML/PDF invoices organized by month
│   └── docs 2025/               <- Original source Word documents (.docx backups)
│
├── images/                      <- Optimized product & category images
├── tests/                       <- Python and Node.js automated test suites
└── tools/                       <- Build scripts and data utilities
    ├── build_catalog.py         <- Main catalog compiler
    ├── audit/                   <- Catalog data verification scripts
    ├── extract/                 <- Word DOCX table & image extraction utilities
    └── maintenance/             <- Data migration and normalization tools
```

---

## 🛠️ Data Management Reference

### Adding or Editing Products (`data/catalog_data.csv`)
| Column | Description | Example |
|---|---|---|
| `sr_number` | Unique product identifier (Group.Item format) | `1.1`, `2.5`, `18.12` |
| `category` | Product category header | `TEFLON TUBE`, `Capacitors` |
| `item_name` | Full item title & specification | `Teflon Tube 1mm White` |
| `size` | Size description | `1.0mm` |
| `list_price` | Selling price in INR (leave blank for *Price on request*) | `450.00` |
| `unit` | Selling unit | `Mtr.`, `Coil`, `Pcs.` |
| `packing` | Standard package quantity | `100 Mtr.` |
| `hsn_code` | 8-digit GST HSN classification code | `39173100` |
| `image_ref` | Image filename in `images/` (without `.png`) | `1.1` |
| `hidden` | Set to `true` to hide item from public catalog | `false` |

### Updating Company Details
Edit **`data/config.json`** to change phone numbers, addresses, sales contact names, or default GST rates.

---

## 🧪 Testing & Validation

Install Python build deps once:
```bash
pip install -r requirements.txt
```

Run all automated checks locally:
```bash
# Rebuild the catalog HTML files manually
python tools/build_catalog.py

# Run Python data integrity and build tests
python -m unittest discover -s tests -p "test_*.py"

# Run Node.js commerce & checkout logic tests
node tests/order_core.test.js
node tests/client_directory.test.js
node tests/bill_archive.test.js
```
*(Or simply run `update.bat`, which runs all of these automatically before pushing).*
