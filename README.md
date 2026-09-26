# GSC / S. Kumar Catalog Management System

**General Supply Corporation / S. Kumar & Bros.**
Price List & Product Catalog Generator

## Quick Start

```bash
# From this directory: validate the data and rebuild both catalogs
python build_catalog.py

# Run the catalog and commerce tests
python -m unittest discover -s tests -p "test_*.py"
node tests/order_core.test.js
```

This creates two files directly in the repository root:
- **print_catalog.html** - Print-ready catalog (Ctrl+P in browser -> Save as PDF)
- **search_catalog.html** - Searchable web catalog with filters

The public pages are:
- [Search catalog](https://shaumitraparikh.github.io/SKumarDirectory/search_catalog.html)
- [Print catalog](https://shaumitraparikh.github.io/SKumarDirectory/print_catalog.html)

Catalog source, assets, templates, tests, and generated pages live at the
repository root (with only supporting folders), removing the nested
catalog-directory segment from both page URLs.

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
├── search_catalog.html          <- GENERATED searchable catalog
├── print_catalog.html           <- GENERATED print catalog
├── 1_Click_Update.bat           <- Rebuild, test, ask before commit/push
├── build_catalog.py             <- Catalog generator for local and Pages builds
├── config.json                  <- Company and checkout configuration
├── data/
│   ├── catalog_data.csv         <- EDIT this product list
│   └── catalog_data_notes.json  <- Source ambiguity/review notes
├── images/                      <- Product images
│   ├── photo_image1.png
│   ├── list_image1.png
│   └── ...
├── templates/
│   ├── print_template.html      <- Print catalog template
│   └── search_template.html     <- Search catalog template
├── assets/
│   ├── css/search_catalog.css   <- Storefront and cart styling
│   └── js/
│       ├── commerce_core.js     <- Tested totals, validation, order schema
│       └── search_catalog.js    <- Browser cart and checkout behavior
├── tests/
│   ├── test_catalog.py          <- CSV, assets, and rendered page checks
│   └── order_core.test.js       <- Checkout math and payload checks
└── README.md                    <- This file
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

The numbered product serials must remain unique and sequential. The builder
rejects malformed or negative prices and gaps/duplicates in serial numbers.
An empty price is intentionally represented as **Price on request**; the system
does not infer or invent a selling price. The one missing HSN for Sr. 71 was
filled using the unanimous HSN of its PVC cord-and-pipe peers. Sr. 303's
malformed `50.00 .00` extraction was checked against the Word source and
corrected to ₹50. Sr. 393's source cell lists both ₹280 and ₹190 but does not
identify the applicable variant; it remains price-on-request, with both
source values and the reason recorded in `data/catalog_data_notes.json`.
Missing exact product photos may use a clearly labelled category
representative image; the source `image_ref` is not overwritten. Optional
dimensions and packing remain blank unless a source supplies them.

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

The Python tests verify serial integrity, the manually added Sr. 1412, the
source-backed Sr. 71 HSN, intentional quote-only pricing, representative-image
fallbacks, and rendered storefront output. The Node tests cover INR rounding,
discount/tax totals, Indian mobile/GSTIN/PIN validation, quote-only order lines,
the stable order payload, and safe cart restoration. GitHub Actions runs both
suites before publishing.

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

## Requirements

- Python 3.x
- Jinja2 (`pip install jinja2`) - for building catalogs
- Node.js - for checkout tests (not required to view the static pages)

## Company Info

Edit `config.json` to update company name, phone, address, date, etc.
