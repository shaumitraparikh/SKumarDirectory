# GSC / S. Kumar Catalog Management System

**General Supply Corporation / S. Kumar & Bros.**
Price List & Product Catalog Generator

## Quick Start

```bash
# From this directory: validate the data and rebuild customer and seller pages
python tools/build_catalog.py

# Run the catalog and commerce tests
python -m unittest discover -s tests -p "test_*.py"
node tests/order_core.test.js
node tests/client_directory.test.js
node tests/bill_archive.test.js
node tests/bill_archive.test.js
```

This creates three files directly in the repository root:
- **print_catalog.html** - Print-ready catalog (Ctrl+P in browser -> Save as PDF)
- **customer_catalog.html** - Customer-facing searchable catalog
- **search_catalog.html** - Seller catalog editor; use only through the local seller server

The public pages are:
- [Customer search catalog](https://shaumitraparikh.github.io/SKumarDirectory/search_catalog.html)
- [Print catalog](https://shaumitraparikh.github.io/SKumarDirectory/print_catalog.html)

### Local seller catalog editor

On Windows, double-click `tools/seller/start_seller.bat`. It starts a local-only
server bound to `127.0.0.1:8766` and opens the seller catalog. Do not change the
loopback bind address. The seller editor API rejects non-local hosts and
cross-origin requests; the Pages deployment copies only `customer_catalog.html`
as the public `search_catalog.html`, never the seller page or `tools/seller/`.

Edit a product to change any CSV field, add a new product (the next unused
serial is suggested), hide/show it on the customer site, or delete it. Hidden
rows remain in the canonical CSV and seller page but are omitted from customer
catalog and print output. **Save & run updater** validates and writes the CSV,
then runs `1_Click_Update.bat /local` to rebuild both pages and execute tests.
Every saved change is snapshotted in a git-ignored local history file so
**Undo last change** also works after a reload. Price and identifier validation
matches the normal catalog builder.

The local save does not automatically push. Publishing uses the normal
`1_Click_Update.bat` confirmation. Before staging or pushing it queries the
public GitHub Actions API and blocks publication at 20 `deploy-pages.yml` push
runs in the current UTC month (configurable with `SKUMAR_PAGES_RUN_LIMIT`).
If GitHub usage cannot be checked, publishing fails closed. This run-count cap
is intentionally conservative; it is not a billing-minute guarantee for other
workflows or repositories.

Catalog pages and the build entry point stay at the repository root to preserve
the short Pages URLs. Supporting code and data are grouped into root-level
folders; maintenance utilities and their reports are organized under `tools/`.

The search catalog includes a browser-persisted cart, customer and delivery
details, item discounts, a proforma estimate, and an order-request handoff.
CGST and SGST default to 9% each (18% total) and can be adjusted. Tax is
estimated on priced items after discounts; sales must confirm tax treatment,
availability, and delivery charges.
The print catalog starts with the source price-list business and sales-contact
header. Product dimensions such as base-bar L/F size and Teflon ID/OD sizes are
stored and shown as distinct specifications.

## GitHub Pages

Pushing to `main` automatically builds and deploys both catalogs to GitHub Pages.
The repository landing page links to the searchable and print-ready catalogs.
On Windows, `1_Click_Update.bat` rebuilds both HTML files, runs the test suites,
and asks before committing and pushing the root-level catalog, workflow, and
generated files. Enter `Y` to publish the update to `origin/main`; otherwise it
leaves the rebuilt files unpublished. Run it from a cleanly synchronized
checkout on the `main` branch with Git, Python, Node.js, and Git credentials
configured. The updater stops before building or committing if local `main` is
not exactly at `origin/main`; synchronize the branch first rather than risking
unrelated commits. It uses a regular non-force push. GitHub Actions independently
rebuilds and tests both pages before publishing the HTML, storefront assets, and
images.

## Folder Structure

```
.
├── index.html                   <- Pages landing page and catalog links
├── search_catalog.html          <- GENERATED local seller editor (not deployed)
├── customer_catalog.html        <- GENERATED customer-facing search catalog
├── print_catalog.html           <- GENERATED print catalog
├── 1_Click_Update.bat           <- Rebuild, test, ask before commit/push
├── tools/build_catalog.py             <- Catalog generator for local and Pages builds
├── generated_bills/             <- Local, git-ignored bill archive
│   └── YYYY-MM/                 <- Monthly standalone proforma bills
├── data/docs 2025/                   <- Original source price list and photo documents
│   └── source images without serial/ <- Source images lacking a product serial
├── data/
│   ├── config.json              <- Company and checkout configuration
│   ├── catalog_data.csv         <- Canonical, reviewed product list
│   │                                hidden column controls public visibility
│   ├── catalog_data_notes.json  <- Source ambiguity/review notes
│   ├── image_serial_map.json    <- Exact image-to-serial and group/item mappings
│   ├── catalog_extraction_draft*.csv <- Optional, unreviewed source imports
│   ├── client_data.csv          <- Private local customer list (git-ignored)
│   └── client_data.example.csv  <- Customer CSV column template
├── images/                      <- Product images
│   ├── sr_0004_group_0001_item_0004_art_silk_tube_sleeves_4mm.png
│   ├── group_0002_sr_9-20_fibreglass_yellow_tube.png
│   └── ...
├── templates/
│   ├── print_template.html      <- Print catalog template
│   └── search_template.html     <- Search catalog template
├── assets/
│   ├── css/search_catalog.css   <- Storefront and cart styling
│   └── js/
│       ├── bill_archive.js      <- Local monthly bill archive and viewer
│       ├── client_directory_core.js <- Private CSV parsing and customer lookup
│       ├── commerce_core.js     <- Tested totals, validation, order schema
│       └── search_catalog.js    <- Browser cart and checkout behavior
├── tests/
│   ├── test_catalog.py          <- CSV, assets, and rendered page checks
│   ├── test_end_to_end.py       <- Build, source coverage, payload, and asset tests
│   ├── order_core.test.js       <- Checkout math and payload checks
│   ├── client_directory.test.js <- Private customer CSV parsing and lookup
│   ├── bill_archive.test.js     <- Monthly bill archive and folder-write checks
│   └── run_one_click_smoke.ps1  <- Windows updater no-publish integration test
├── tools/
│   ├── audit/                   <- Catalog and image audit utilities
│   ├── extract/                 <- Source document extraction utilities
│   ├── maintenance/             <- Manual data/image repair utilities
│   ├── seller/                  <- Loopback-only editor and Actions cap guard
│   └── reports/                 <- Generated and diagnostic reports
└── README.md                    <- This file
```

The DOCX files in `data/docs 2025/` are retained as source backups. Edit and maintain
the canonical product data in `data/catalog_data.csv`; the document extractors
write separate draft CSVs under `data/` so an import cannot silently replace
reviewed data. Source serials 1350-1360 have no product particulars and are
explicitly marked for business review rather than filled by inference. Product
Sr. 1412 was added to the canonical CSV and is not present in the numbered
source rows.

Add customer records to the git-ignored `data/client_data.csv` using the
columns in `data/client_data.example.csv`. In the order panel, choose **Load
customer list (CSV)** and select that local file, then search and select a
customer to fill the form. Customer data stays in page memory; it is not
embedded in the public GitHub Pages output, saved in browser storage, or
uploaded until the user submits an order. Manual entry remains available.
Customer details and the order item list can each be expanded or collapsed,
while estimated totals and order actions stay visible.

Generated proforma bills are saved as standalone HTML files under
`generated_bills/YYYY-MM/` and are excluded from Git. The first time a bill is
printed, choose the repository's `generated_bills` folder when the browser asks
for folder access; month folders are created automatically. Use **View saved
bills** in the order panel to browse by month and open an archived bill. Browsers
without local folder access keep bills in that browser's local archive and
download a copy instead. Bill contents remain on the user's device and are not
included in GitHub Pages deployments.

The scripts under `tools/` are manual utilities, not part of the one-click
catalog build or GitHub Pages deployment. Run them from any working directory;
they resolve the repository root from their own file location. For example:

```bash
python tools/audit/check_gen.py
```

## How to Update Prices / Add Items

1. Open `data/catalog_data.csv` in Excel
2. Edit prices, add new rows with the next serial number, or update item names
3. Save the CSV file
4. Run `1_Click_Update.bat` from the repository's synchronized `main` checkout
   to validate, rebuild, and test the source and generated catalogs
5. Enter `Y` to commit and push the tested update; any other response leaves it
   rebuilt but unpublished
6. Wait for the success message; GitHub Actions then deploys both pages
7. Open the generated HTML files locally, or visit the root-level URLs above
   after the Pages workflow finishes

`sr_number` is the permanent, unique product key used by the catalog, search
index, cart, and order SKU. Do not renumber existing products: deleted serials
remain unused, and new products receive the next unused serial. Each row also
has a stable `group_number.item_number` label; groups follow catalog category
sections, and new items in a group use its next unused item number. Removing an
item does not require renumbering its neighbors. The builder rejects invalid or
duplicate serials and duplicate hierarchical labels. An empty price is
intentionally represented as **Price on request**; the system does not infer or
invent a selling price. The one missing HSN for Sr. 71 was
filled using the unanimous HSN of its PVC cord-and-pipe peers. Sr. 303's
malformed `50.00 .00` extraction was checked against the Word source and
corrected to ₹50. Sr. 393's source cell lists both ₹280 and ₹190 but does not
identify the applicable variant; it remains price-on-request, with both
source values and the reason recorded in `data/catalog_data_notes.json`.
Missing exact product photos may use a clearly labelled category
representative image; the source `image_ref` is not overwritten. Optional
dimensions and packing remain blank unless a source supplies them.
Catalog-linked image filenames include their exact `sr_number` or compact
serial ranges plus the corresponding group and item ID(s). Shared images within
one group include the mapped item-number ranges; images spanning groups include
the group range. `data/image_serial_map.json` keeps the exact membership for
each filename.
The source-photo document uses category-level pictures rather than per-item
serials; those pictures are associated with the serial range for the matching
catalog group, not treated as individual product photos.
`data/image_serial_map.json` records the exact serial and group-item membership
for every image asset. All 411 embedded price-list product photos are byte
verified against their mapped catalog image. The 80 unique category-photo
images are retained as serial-tagged assets; two additional extracted files
had no source serial and are kept outside the published `images/` directory
rather than assigned invented product numbers.

## Customer Orders and Payment Integration

The current GitHub Pages site is static. Customers can add priced and
price-on-request items, provide Indian mobile/address/PIN/state details, and
open a WhatsApp order request to the configured sales contact. The handoff
includes a versioned JSON-compatible order with SKU (serial), customer,
specifications, quantities, discounts, INR estimates, and explicit
`awaiting_merchant_confirmation` / `not_started` payment status. Customers can
download that structured request for backup. Only the cart identifiers,
quantities, discounts, and tax-rate inputs are stored in the browser; customer
details are not saved to browser storage. The order request remains on the
customer's device until they choose to send/open WhatsApp. The message and
proforma clearly say that no payment was collected.

**Online payment is not enabled in this static release.** Do not put gateway
secrets in HTML, JavaScript, or GitHub Pages configuration. For an India-first
Razorpay integration, deploy a secured HTTPS backend that:

1. Accepts the stable `schema_version: 1` order request and validates customer
   input, catalog SKUs, current prices, discounts, stock, shipping, and GST
   server-side (never trust browser totals).
2. Creates an idempotent server-side order and Razorpay checkout using secrets
   held only in server environment/secret storage; returns a hosted HTTPS
   `checkout_url` to the storefront.
3. Verifies signed payment webhooks server-side, records order/payment state,
   and exposes a status lookup. Never mark an order paid from a browser redirect.
4. Applies applicable intra/inter-state GST and produces a compliant tax
   invoice only after the business confirms registration, place of supply, and
   tax rules.

The storefront has a provider boundary (`checkout.provider`, currently
`whatsapp`) and an optional `api_base_url`; selecting `razorpay` without that
secure API fails clearly without charging the customer. Shopify is an
alternative hosted commerce platform, not a credential-free payment switch;
it additionally needs a Shopify store and variant mapping for each catalog SKU.
Choose one operational platform and configure its account, server, policies,
shipping, inventory, and credentials before enabling paid checkout.

## Validation and Tests

The Python tests verify serial integrity, source-document coverage, full catalog
payload preservation, generated asset links, and the build from an unrelated
working directory, as well as the manually added Sr. 1412, source-backed Sr. 71
HSN, quote-only pricing, and representative-image fallbacks. The Node tests
cover INR rounding, discount/tax totals, Indian mobile/GSTIN/PIN validation,
quote-only order lines, the stable order payload, safe cart restoration, and
customer CSV parsing and lookup.
GitHub Actions also runs the actual Windows one-click updater in no-publish
mode to verify its build and test gates without committing or pushing.

## CSV Columns

| Column | Description | Example |
|--------|-------------|---------|
| sr_number | Permanent unique product serial | 138 |
| group_number | Stable category-section number | 6 |
| item_number | Stable number within the group; display as `group_number.item_number` | 3 |
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

## Requirements

- Python 3.x
- Jinja2 (`pip install jinja2`) - for building catalogs
- python-docx and Pillow - for source-document extraction and image audits
- Node.js - for checkout tests (not required to view the static pages)

## Company Info

Edit `data/config.json` to update company name, phone, address, date, etc.
