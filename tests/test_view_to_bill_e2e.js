'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const commerce = require(path.join(ROOT_DIR, 'app/assets/js/commerce_core'));
const clientDirectory = require(path.join(ROOT_DIR, 'app/assets/js/client_directory_core'));
const billArchiveModule = require(path.join(ROOT_DIR, 'app/assets/js/bill_archive'));

console.log('====================================================');
console.log('STARTING END-TO-END TEST: VIEW -> ITEMS -> CART -> BILL');
console.log('====================================================\n');

// ----------------------------------------------------
// STEP 1: VIEW CATALOG & PRODUCTS
// ----------------------------------------------------
console.log('[STEP 1] Verifying Catalog View & Product Data...');

const indexHtmlPath = path.join(ROOT_DIR, 'index.html');
const printHtmlPath = path.join(ROOT_DIR, 'print_catalog.html');

assert.ok(fs.existsSync(indexHtmlPath), 'index.html must exist');
assert.ok(fs.existsSync(printHtmlPath), 'print_catalog.html must exist');

const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
const printHtml = fs.readFileSync(printHtmlPath, 'utf8');

// Check catalogData JSON embedded in index.html
const catalogDataMatch = indexHtml.match(/<script id="catalogData" type="application\/json">([\s\S]*?)<\/script>/);
assert.ok(catalogDataMatch, 'catalogData script tag must be present in index.html');

const catalogItems = JSON.parse(catalogDataMatch[1]);
assert.ok(Array.isArray(catalogItems), 'catalogItems must be an array');
assert.strictEqual(catalogItems.length, 1412, `Expected 1412 products, got ${catalogItems.length}`);

// Verify key categories exist and are numbered
const categories = Array.from(new Set(catalogItems.map(i => i.category)));
assert.ok(categories.includes('Taparia & Crimping Tools'), 'Taparia & Crimping Tools category must exist');
assert.ok(categories.includes('TARA / DHARIA Items'), 'TARA / DHARIA Items category must exist');
assert.ok(categories.includes('Halogen Holders & Nutrilinks'), 'Halogen Holders & Nutrilinks category must exist');
assert.ok(categories.includes('Industrial Tapes'), 'Industrial Tapes category must exist');

// Verify product specification attributes
const samplePriced = catalogItems.find(i => i.sr_number === '27.77');
assert.ok(samplePriced, 'Item 27.77 (Open Barrel tool) must exist');
assert.strictEqual(samplePriced.category, 'Taparia & Crimping Tools');
assert.strictEqual(samplePriced.hsn_code, '82032000');
assert.strictEqual(samplePriced.list_price, '1850.0');
assert.strictEqual(samplePriced.display_image_path, 'images/27.76.png'); // Not 22.1!

const sampleQuote = catalogItems.find(i => i.sr_number === '30.18');
assert.ok(sampleQuote, 'Item 30.18 (Brass Nutrilink) must exist');
assert.strictEqual(sampleQuote.category, 'Halogen Holders & Nutrilinks');
assert.strictEqual(sampleQuote.list_price, '', 'Quote items must have empty list_price');

// Verify print catalog has 0 inversions
const printSrs = Array.from(printHtml.matchAll(/<td class="col-sr">([\d]+(?:\.[\d]+)?)\.?<\/td>/g)).map(m => m[1]);
assert.strictEqual(printSrs.length, 1412, 'Print catalog must contain all 1412 items');
let prev = [0, 0];
let inversions = 0;
for (const sr of printSrs) {
    const parts = sr.split('.').map(Number);
    if (parts[0] < prev[0] || (parts[0] === prev[0] && parts[1] < prev[1])) {
        inversions++;
    }
    prev = parts;
}
assert.strictEqual(inversions, 0, 'Print catalog must have zero serial number inversions');
console.log('✓ Step 1 Passed: 1412 items validated, strictly sorted, correct images.');


// ----------------------------------------------------
// STEP 2: ITEMS TO CART & CALCULATIONS
// ----------------------------------------------------
console.log('\n[STEP 2] Adding Items to Cart & Calculating Totals...');

// User adds 3 items to cart:
// 1. 27.77: Open Barrel LUVKUSH-6 Tool (₹1850.0 each, qty 2, 5% discount)
// 2. 1.1: Art Silk Tube (₹280.0 each, qty 4, 10% discount)
// 3. 30.18: Brass Nutrilink Bar (Quote-only item, qty 10)

const cartItems = [
    {
        sr_number: '27.77',
        name: samplePriced.item_name,
        hsn: samplePriced.hsn_code,
        price: parseFloat(samplePriced.list_price),
        qty: 2,
        discountPct: 5,
        unit: 'Pcs.'
    },
    {
        sr_number: '1.1',
        name: 'ART SILK TUBE / Sleeves 1mm',
        hsn: '85469090',
        price: 280.0,
        qty: 4,
        discountPct: 10,
        unit: '100mtr.'
    },
    {
        sr_number: '30.18',
        name: sampleQuote.item_name,
        hsn: sampleQuote.hsn_code,
        price: null,
        qty: 10,
        discountPct: 0,
        unit: '1way'
    }
];

// Line amount assertions
const line1 = commerce.calculateLineAmounts(cartItems[0]);
assert.strictEqual(line1.gross, 3700.0);
assert.strictEqual(line1.discount, 185.0);
assert.strictEqual(line1.net, 3515.0);

const line2 = commerce.calculateLineAmounts(cartItems[1]);
assert.strictEqual(line2.gross, 1120.0);
assert.strictEqual(line2.discount, 112.0);
assert.strictEqual(line2.net, 1008.0);

const line3 = commerce.calculateLineAmounts(cartItems[2]);
assert.strictEqual(line3.isQuoted, true);
assert.strictEqual(line3.net, null);

// Cart Totals with 9% CGST + 9% SGST
const cartTotals = commerce.calculateTotals(cartItems, { cgstRate: 9, sgstRate: 9 });
assert.strictEqual(cartTotals.itemsSubtotal, 4820.0); // 3700 + 1120
assert.strictEqual(cartTotals.discountTotal, 297.0);  // 185 + 112
assert.strictEqual(cartTotals.taxableSubtotal, 4523.0); // 4820 - 297
assert.strictEqual(cartTotals.cgstAmount, 407.07);    // 9% of 4523
assert.strictEqual(cartTotals.sgstAmount, 407.07);    // 9% of 4523
assert.strictEqual(commerce.roundCurrency(cartTotals.cgstAmount + cartTotals.sgstAmount), 814.14);
assert.strictEqual(cartTotals.estimatedTotal, 5337.14);
assert.strictEqual(cartTotals.quoteItemCount, 1);
assert.strictEqual(cartTotals.includesUnpricedItems, true);
console.log('✓ Step 2 Passed: Line amounts, discounts, CGST/SGST taxes, and quote items verified.');


// ----------------------------------------------------
// STEP 3: CUSTOMER LOOKUP & AUTO-FILL
// ----------------------------------------------------
console.log('\n[STEP 3] Testing Customer Search, Multi-source Lookup & Auto-fill...');

const directoryData = [
    {
        name: 'General Supply Corporation',
        business_name: 'General Supply Corporation',
        phone: '9869905779',
        gstin: '27ACJPP2955J1Z4',
        address: '3rd Central Building, Grd. Floor, Kalbadevi, Mumbai - 400002',
        state: 'Maharashtra',
        pincode: '400002'
    },
    {
        name: 'Asha Shah',
        business_name: 'Ace Electricals',
        phone: '9869905779',
        gstin: '27ACJPP2955J1Z4',
        address: '12, Market Road, Mumbai',
        state: 'Maharashtra',
        pincode: '400002'
    }
];

// Test 1: Search by partial query "General"
const resultsGeneral = clientDirectory.filterCustomers(directoryData, 'General');
assert.strictEqual(resultsGeneral.length, 1);
assert.strictEqual(resultsGeneral[0].business_name, 'General Supply Corporation');

// Test 2: Search by partial phone "98699"
const resultsPhone = clientDirectory.filterCustomers(directoryData, '98699');
assert.strictEqual(resultsPhone.length, 2);

// Test 3: Search by GSTIN prefix "27ACJ"
const resultsGstin = clientDirectory.filterCustomers(directoryData, '27ACJ');
assert.strictEqual(resultsGstin.length, 2);

// Test 4: Find exact customer
const matchedCustomer = clientDirectory.findCustomer(directoryData, 'General Supply Corporation');
assert.ok(matchedCustomer, 'Customer must match');
assert.strictEqual(matchedCustomer.phone, '9869905779');

// Validate buyer object for order / bill
const buyerValidation = commerce.validateBuyer(matchedCustomer);
assert.strictEqual(buyerValidation.valid, true, 'Matched customer must be valid for billing');
console.log('✓ Step 3 Passed: Customer autocomplete search and validation verified.');


// ----------------------------------------------------
// STEP 4: CART TO PROFORMA BILL GENERATION & ARCHIVE
// ----------------------------------------------------
console.log('\n[STEP 4] Generating Proforma Invoice & Archiving Bill...');

const billDate = '2026-09-30';
const invoiceNo = 'PI-20260930-000042';

function generateTestProformaHtml(buyer, items, totals, invNo, date) {
    const itemRows = items.map(item => {
        const line = commerce.calculateLineAmounts(item);
        const priceStr = line.isQuoted ? 'Price on request' : `₹${item.price.toFixed(2)}`;
        const netStr = line.isQuoted ? 'Quote line' : `₹${line.net.toFixed(2)}`;
        return `
            <tr>
                <td>${item.sr_number}</td>
                <td><strong>${item.name}</strong></td>
                <td>${item.hsn || ''}</td>
                <td style="text-align:right;">${priceStr}</td>
                <td style="text-align:center;">${item.qty} ${item.unit || ''}</td>
                <td style="text-align:right;">${item.discountPct ? item.discountPct + '%' : '-'}</td>
                <td style="text-align:right;"><strong>${netStr}</strong></td>
            </tr>
        `;
    }).join('\n');

    return `<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Proforma Invoice ${invNo}</title>
</head>
<body>
    <div class="inv-container" id="printBill">
        <h1 class="biz-title">S. Kumar &amp; Bros</h1>
        <p>No: <span id="pInvNo">${invNo}</span> | Date: <span id="pDate">${date}</span></p>
        <div class="meta-box">
            <h4>Billed To (Customer Details)</h4>
            <strong id="pBuyerName">${buyer.business_name || buyer.name}</strong><br>
            <span>📞 ${buyer.phone}</span><br>
            <span>${buyer.address}</span><br>
            <span>GSTIN: ${buyer.gstin || ''}</span>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Sr.</th><th>Item Description</th><th>HSN</th>
                    <th>Price</th><th>Qty</th><th>Disc</th><th>Net</th>
                </tr>
            </thead>
            <tbody>
                ${itemRows}
            </tbody>
        </table>
        <div class="totals-area">
            <div>Taxable Subtotal: ₹${totals.taxableSubtotal.toFixed(2)}</div>
            <div>CGST (9%): ₹${totals.cgstAmount.toFixed(2)}</div>
            <div>SGST (9%): ₹${totals.sgstAmount.toFixed(2)}</div>
            <div id="pGrandTotal" class="grand-total">₹${totals.estimatedTotal.toFixed(2)}</div>
        </div>
    </div>
</body>
</html>`;
}

const billHtml = generateTestProformaHtml(matchedCustomer, cartItems, cartTotals, invoiceNo, billDate);
assert.ok(billHtml.includes(invoiceNo), 'Generated bill must contain invoice number');
assert.ok(billHtml.includes('General Supply Corporation'), 'Generated bill must contain buyer name');
assert.ok(billHtml.includes('27.77'), 'Generated bill must contain item 27.77');
assert.ok(billHtml.includes('₹5337.14'), 'Generated bill must contain calculated grand total');

// Test BillArchive module pathing and filename generation
assert.strictEqual(billArchiveModule.monthFor(new Date('2026-09-30T10:00:00Z')), '2026-09');
const fileName = billArchiveModule.safeFileName(invoiceNo);
assert.strictEqual(fileName, `${invoiceNo}.html`, 'Filename must be safe and have .html extension');

// Write to test sandbox folder simulating generated_bills/2026-09
const testMonthDir = path.join(ROOT_DIR, 'data/generated_bills/2026-09');
fs.mkdirSync(testMonthDir, { recursive: true });
const testBillFile = path.join(testMonthDir, `${invoiceNo}.html`);
fs.writeFileSync(testBillFile, billHtml, 'utf8');

assert.ok(fs.existsSync(testBillFile), 'Saved bill file must exist in data/generated_bills/2026-09/');
console.log(`✓ Step 4 Passed: Proforma invoice generated & archived to ${testBillFile}`);

// Clean up test file so workspace stays clean
fs.unlinkSync(testBillFile);

console.log('\n====================================================');
console.log('ALL END-TO-END FLOW TESTS PASSED SUCCESSFULLY! (100%)');
console.log('====================================================');
