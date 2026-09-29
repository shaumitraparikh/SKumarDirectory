'use strict';

const assert = require('assert');
const commerce = require('../app/assets/js/commerce_core');

const validBuyer = {
    name: 'Test Buyer',
    phone: '9869905779',
    email: 'buyer@example.in',
    address: '12 Test Market Road',
    state: 'Maharashtra',
    pincode: '400002',
    gstin: '27ACJPP2955J1Z4'
};

const pricedItem = {
    sr_number: '65.1',
    name: 'Test lamp',
    hsn: '94059900',
    price: 996,
    qty: 1,
    discountPct: 10,
    unit: 'Pcs.'
};

function expectThrow(callback, pattern) {
    assert.throws(callback, pattern);
}

assert.strictEqual(commerce.roundCurrency(0.1 + 0.2), 0.3);
assert.deepStrictEqual(commerce.calculateLineAmounts({
    price: 100,
    qty: 3,
    discountPct: 10
}), { isQuoted: false, gross: 300, discount: 30, net: 270 });
assert.deepStrictEqual(commerce.calculateLineAmounts({
    price: null,
    qty: 2,
    discountPct: 0
}), { isQuoted: true, gross: null, discount: null, net: null });

const totals = commerce.calculateTotals([
    pricedItem,
    { sr_number: '781', name: 'Custom part', price: null, qty: 2, discountPct: 0 }
], { cgstRate: 9, sgstRate: 9 });
assert.strictEqual(totals.taxableSubtotal, 896.4);
assert.strictEqual(totals.discountTotal, 99.6);
assert.strictEqual(totals.cgstAmount, 80.68);
assert.strictEqual(totals.sgstAmount, 80.68);
assert.strictEqual(totals.estimatedTotal, 1057.76);
assert.strictEqual(totals.quoteItemCount, 1);
assert.strictEqual(totals.includesUnpricedItems, true);

assert.strictEqual(commerce.normalizeIndianMobile('09869905779'), '919869905779');
assert.strictEqual(commerce.normalizeIndianMobile('+91 98699 05779'), '919869905779');
assert.strictEqual(commerce.normalizeIndianMobile('12345'), null);
assert.strictEqual(commerce.validateBuyer(validBuyer).valid, true);
assert.strictEqual(commerce.validateBuyer(Object.assign({}, validBuyer, { gstin: 'bad' })).valid, false);
assert.strictEqual(commerce.validateBuyer(Object.assign({}, validBuyer, { pincode: '000000' })).valid, false);
expectThrow(() => commerce.calculateTotals([], { cgstRate: -1, sgstRate: 9 }), /between 0% and 100%/);
expectThrow(() => commerce.calculateLineAmounts({ price: 1, qty: 10000, discountPct: 0 }), /Quantity/);

const order = commerce.createOrder({
    id: 'SK-20260926-000001',
    createdAt: '2026-09-26T12:00:00.000Z',
    buyer: validBuyer,
    items: [pricedItem, { sr_number: '781', name: 'Custom part', price: null, qty: 2, unit: 'Pcs.' }],
    rates: { cgstRate: 9, sgstRate: 9 }
});
assert.strictEqual(order.currency, 'INR');
assert.strictEqual(order.status, 'awaiting_merchant_confirmation');
assert.strictEqual(order.payment.status, 'not_started');
assert.strictEqual(order.customer.phone, '919869905779');
assert.strictEqual(order.items[0].sku, '65.1');
assert.strictEqual(order.items[1].unit_price, null);
assert.strictEqual(order.amounts.estimate_excludes_unpriced_items, true);
assert.ok(/No payment has been taken/.test(commerce.formatOrderMessage(order)));
assert.ok(/price to be confirmed/.test(commerce.formatOrderMessage(order)));
assert.ok(/Sr 65\.1/.test(commerce.formatOrderMessage(order)));

const legacyOrder = commerce.createOrder({
    id: 'SK-20260926-000002',
    createdAt: '2026-09-26T12:01:00.000Z',
    buyer: validBuyer,
    items: [{ sr_no: '99', name: 'Legacy cart item', price: 1, qty: 1 }],
    rates: { cgstRate: 0, sgstRate: 0 }
});
assert.strictEqual(legacyOrder.items[0].sku, '99');

const restored = commerce.sanitizeCartSnapshot({
    version: 1,
    items: {
        1412: { qty: 2, discountPct: 5, price: 0 },
        9999: { qty: 1, discountPct: 0 },
        781: { qty: 10000, discountPct: 0 }
    },
    rates: { cgstRate: 9, sgstRate: 9 }
}, { 1412: true, 781: true });
assert.strictEqual(restored.items['1412'].qty, 2);
assert.strictEqual(restored.items['1412'].discountPct, 5);
assert.strictEqual(restored.discardedItems, 2);
assert.strictEqual(restored.rates.cgstRate, 9);

console.log('PASS: order calculations, quote-only lines, GST/contact validation, payload, and cart restoration.');
