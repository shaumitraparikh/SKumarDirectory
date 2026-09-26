(function (root, factory) {
    const commerce = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = commerce;
    } else {
        root.CatalogCommerce = commerce;
    }
}(typeof window !== 'undefined' ? window : global, function () {
    'use strict';

    const MAX_QUANTITY = 9999;
    const GSTIN_PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
    const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    function roundCurrency(value) {
        if (!Number.isFinite(value)) {
            throw new TypeError('Currency amounts must be finite numbers.');
        }
        return Math.round((value + Number.EPSILON) * 100) / 100;
    }

    function calculateLineAmounts(item) {
        const quantity = Number(item.qty);
        const discountPct = Number(item.discountPct || 0);
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > MAX_QUANTITY) {
            throw new RangeError('Quantity must be a whole number from 1 to 9,999.');
        }
        if (!Number.isFinite(discountPct) || discountPct < 0 || discountPct > 100) {
            throw new RangeError('Item discount must be between 0% and 100%.');
        }

        if (item.price === null || item.price === undefined || item.price === '') {
            return { isQuoted: true, gross: null, discount: null, net: null };
        }

        const price = Number(item.price);
        if (!Number.isFinite(price) || price < 0) {
            throw new RangeError('Item price must be a non-negative number or left unpriced.');
        }
        const gross = roundCurrency(price * quantity);
        const discount = roundCurrency(gross * discountPct / 100);
        return { isQuoted: false, gross, discount, net: roundCurrency(gross - discount) };
    }

    function calculateTotals(items, rates) {
        const cgstRate = Number(rates.cgstRate);
        const sgstRate = Number(rates.sgstRate);
        if (![cgstRate, sgstRate].every(rate => Number.isFinite(rate) && rate >= 0 && rate <= 100)) {
            throw new RangeError('CGST and SGST rates must each be between 0% and 100%.');
        }

        let itemsSubtotal = 0;
        let discountTotal = 0;
        let taxableSubtotal = 0;
        let quoteItemCount = 0;
        items.forEach(item => {
            const line = calculateLineAmounts(item);
            if (line.isQuoted) {
                quoteItemCount += 1;
                return;
            }
            itemsSubtotal += line.gross;
            discountTotal += line.discount;
            taxableSubtotal += line.net;
        });

        itemsSubtotal = roundCurrency(itemsSubtotal);
        discountTotal = roundCurrency(discountTotal);
        taxableSubtotal = roundCurrency(taxableSubtotal);
        const cgstAmount = roundCurrency(taxableSubtotal * cgstRate / 100);
        const sgstAmount = roundCurrency(taxableSubtotal * sgstRate / 100);
        const totalTax = roundCurrency(cgstAmount + sgstAmount);
        return {
            itemsSubtotal,
            discountTotal,
            taxableSubtotal,
            cgstRate,
            cgstAmount,
            sgstRate,
            sgstAmount,
            totalRate: roundCurrency(cgstRate + sgstRate),
            totalTax,
            estimatedTotal: roundCurrency(taxableSubtotal + totalTax),
            quoteItemCount,
            includesUnpricedItems: quoteItemCount > 0
        };
    }

    function normalizeIndianMobile(value) {
        let digits = String(value || '').replace(/\D/g, '');
        if (digits.length === 11 && digits.charAt(0) === '0') digits = digits.slice(1);
        if (digits.length === 12 && digits.slice(0, 2) === '91') digits = digits.slice(2);
        if (!/^[6-9][0-9]{9}$/.test(digits)) return null;
        return '91' + digits;
    }

    function validateBuyer(buyer) {
        const errors = [];
        const name = String(buyer.name || '').trim();
        const address = String(buyer.address || '').trim();
        const state = String(buyer.state || '').trim();
        const pincode = String(buyer.pincode || '').trim();
        const email = String(buyer.email || '').trim();
        const gstin = String(buyer.gstin || '').trim().toUpperCase();
        const mobile = normalizeIndianMobile(buyer.phone);

        if (name.length < 2) errors.push('Enter the customer or business name.');
        if (!mobile) errors.push('Enter a valid 10-digit Indian mobile number.');
        if (address.length < 8) errors.push('Enter the complete delivery address.');
        if (!state) errors.push('Select the delivery state or union territory.');
        if (!/^[1-9][0-9]{5}$/.test(pincode)) errors.push('Enter a valid 6-digit Indian PIN code.');
        if (email && !EMAIL_PATTERN.test(email)) errors.push('Enter a valid email address or leave it blank.');
        if (gstin && !GSTIN_PATTERN.test(gstin)) errors.push('Enter a valid 15-character GSTIN or leave it blank.');

        return {
            valid: errors.length === 0,
            errors,
            normalized: { name, phone: mobile, email, address, state, pincode, gstin }
        };
    }

    function createOrder(options) {
        const buyer = validateBuyer(options.buyer);
        if (!buyer.valid) {
            throw new Error(buyer.errors.join(' '));
        }
        if (!Array.isArray(options.items) || options.items.length === 0) {
            throw new Error('Add at least one item before placing an order request.');
        }
        if (!options.id || !options.createdAt) {
            throw new Error('Order reference and creation time are required.');
        }

        const totals = calculateTotals(options.items, options.rates);
        const items = options.items.map(item => {
            const line = calculateLineAmounts(item);
            return {
                sku: String(item.sr_number !== undefined ? item.sr_number : item.sr_no),
                group_number: item.group_number == null ? '' : String(item.group_number),
                item_number: item.item_number == null ? '' : String(item.item_number),
                name: String(item.name),
                hsn: String(item.hsn || ''),
                specification: {
                    size: String(item.size || ''),
                    id_size: String(item.idSize || ''),
                    od_size: String(item.odSize || ''),
                    lf_size: String(item.lfSize || ''),
                    unit: String(item.unit || ''),
                    packing: String(item.packing || '')
                },
                quantity: Number(item.qty),
                unit_price: line.isQuoted ? null : roundCurrency(Number(item.price)),
                discount_percent: line.isQuoted ? 0 : Number(item.discountPct || 0),
                gross_amount: line.isQuoted ? null : line.gross,
                discount_amount: line.isQuoted ? null : line.discount,
                taxable_amount: line.isQuoted ? null : line.net,
                price_status: line.isQuoted ? 'merchant_quote_required' : 'catalog_estimate'
            };
        });

        return {
            schema_version: 1,
            order_reference: String(options.id),
            created_at: String(options.createdAt),
            source: 'skumar_catalog',
            currency: 'INR',
            status: 'awaiting_merchant_confirmation',
            payment: { status: 'not_started', provider: 'not_configured' },
            customer: buyer.normalized,
            items,
            amounts: {
                items_subtotal: totals.itemsSubtotal,
                item_discounts: totals.discountTotal,
                taxable_subtotal: totals.taxableSubtotal,
                cgst_rate: totals.cgstRate,
                cgst_amount: totals.cgstAmount,
                sgst_rate: totals.sgstRate,
                sgst_amount: totals.sgstAmount,
                total_tax: totals.totalTax,
                estimated_total: totals.estimatedTotal,
                unpriced_item_count: totals.quoteItemCount,
                estimate_excludes_unpriced_items: totals.includesUnpricedItems,
                shipping_amount: null
            }
        };
    }

    function sanitizeCartSnapshot(snapshot, validSkus) {
        if (!snapshot || snapshot.version !== 1 || !snapshot.items || typeof snapshot.items !== 'object') {
            throw new TypeError('Saved cart has an unsupported format.');
        }
        const items = Object.create(null);
        let discardedItems = 0;
        Object.keys(snapshot.items).forEach(sku => {
            const item = snapshot.items[sku];
            const quantity = Number(item && item.qty);
            const discountPct = Number(item && item.discountPct || 0);
            if (!validSkus[sku] || !Number.isInteger(quantity) || quantity < 1 || quantity > MAX_QUANTITY ||
                !Number.isFinite(discountPct) || discountPct < 0 || discountPct > 100) {
                discardedItems += 1;
                return;
            }
            items[sku] = { qty: quantity, discountPct };
        });
        const rates = snapshot.rates || {};
        const cgstRate = Number(rates.cgstRate);
        const sgstRate = Number(rates.sgstRate);
        return {
            items,
            discardedItems,
            rates: [cgstRate, sgstRate].every(rate => Number.isFinite(rate) && rate >= 0 && rate <= 100)
                ? { cgstRate, sgstRate }
                : { cgstRate: 9, sgstRate: 9 }
        };
    }

    function formatOrderMessage(order) {
        const lines = [
            'Order request ' + order.order_reference,
            'Customer: ' + order.customer.name,
            'WhatsApp: +' + order.customer.phone,
            'Delivery: ' + order.customer.address + ', ' + order.customer.state + ' - ' + order.customer.pincode
        ];
        if (order.customer.email) lines.push('Email: ' + order.customer.email);
        if (order.customer.gstin) lines.push('GSTIN: ' + order.customer.gstin);
        lines.push('', 'Items:');
        order.items.forEach((item, index) => {
            const details = [item.specification.size, item.specification.id_size && 'ID ' + item.specification.id_size,
                item.specification.od_size && 'OD ' + item.specification.od_size,
                item.specification.lf_size && 'L/F ' + item.specification.lf_size].filter(Boolean).join(', ');
            const price = item.unit_price === null ? 'price to be confirmed' : '₹' + item.unit_price.toFixed(2);
            const groupLabel = item.group_number && item.item_number
                ? ' (' + item.group_number + '.' + item.item_number + ')'
                : '';
            lines.push((index + 1) + '. Sr ' + item.sku + groupLabel + ' — ' + item.name +
                (details ? ' (' + details + ')' : '') + ' | Qty ' + item.quantity + ' ' +
                item.specification.unit + ' | ' + price);
        });
        lines.push(
            '',
            'Priced items taxable subtotal: ₹' + order.amounts.taxable_subtotal.toFixed(2),
            'Estimated CGST + SGST: ₹' + order.amounts.total_tax.toFixed(2),
            'Estimated total: ₹' + order.amounts.estimated_total.toFixed(2)
        );
        if (order.amounts.estimate_excludes_unpriced_items) {
            lines.push('Some items are price-on-request; estimates exclude those items and require confirmation.');
        }
        lines.push('Please confirm availability, final pricing, tax and delivery charges. No payment has been taken.');
        return lines.join('\n');
    }

    return {
        MAX_QUANTITY,
        roundCurrency,
        calculateLineAmounts,
        calculateTotals,
        normalizeIndianMobile,
        validateBuyer,
        createOrder,
        sanitizeCartSnapshot,
        formatOrderMessage
    };
}));
