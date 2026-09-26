const CommerceCore = window.CatalogCommerce;
const CART_STORAGE_KEY = 'skumar-catalog-cart-v1';
const checkoutConfig = document.getElementById('checkoutConfig');
let cart = Object.create(null);
let lastOrder = null;

function toggleCart(forceOpen) {
        const drawer = document.getElementById('cartDropdown');
        const isOpen = drawer.classList.contains('open');
        const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : !isOpen;
        drawer.classList.toggle('open', shouldOpen);
        document.getElementById('cartBackdrop').classList.toggle('open', shouldOpen);
        drawer.setAttribute('aria-hidden', String(!shouldOpen));
        document.querySelector('.cart-toggle-btn').setAttribute('aria-expanded', String(shouldOpen));
        if (shouldOpen) {
            document.querySelector('.close-cart').focus();
        } else {
            document.querySelector('.cart-toggle-btn').focus();
        }
    }

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && document.getElementById('cartDropdown').classList.contains('open')) {
            toggleCart(false);
        }
    });

    function showToast(msg) {
        const t = document.getElementById('toast');
        t.innerText = msg;
        t.className = "show";
        setTimeout(() => { t.className = t.className.replace("show", ""); }, 2000);
    }

    function filterCatalog() {
        const input = document.getElementById('searchInput').value.toLowerCase();
        const cards = document.getElementsByClassName('card');
        for (let i = 0; i < cards.length; i++) {
            const searchData = cards[i].getAttribute('data-search');
            cards[i].style.display = searchData.includes(input) ? 'flex' : 'none';
        }
    }

    function getHsn(sr_no) {
        const card = document.getElementById('name-'+sr_no).closest('.card');
        const hsnSpan = card.querySelector('.hsn-val');
        return hsnSpan ? hsnSpan.innerText.trim() : "";
    }

    function readProduct(sr_no, qty, discountPct) {
        const nameElement = document.getElementById('name-' + sr_no);
        const card = nameElement.closest('.card');
        const priceText = document.getElementById('price-' + sr_no).innerText.trim().replace(/,/g, '');
        const parsedPrice = priceText ? Number(priceText) : null;
        const text = selector => {
            const element = card.querySelector(selector);
            return element && !element.hidden ? element.innerText.trim() : '';
        };
        return {
            sr_no,
            name: nameElement.innerText.trim(),
            price: parsedPrice,
            qty,
            hsn: getHsn(sr_no),
            size: text('.size-val'),
            idSize: text('.id-size-val'),
            odSize: text('.od-size-val'),
            lfSize: text('.lf-size-val'),
            unit: text('.unit-val'),
            packing: text('.packing-val'),
            discountPct: parsedPrice === null ? 0 : discountPct,
            discountOpen: false
        };
    }

    function addToCart(sr_no) {
        const qtyInput = document.getElementById('qty-' + sr_no);
        const qty = Number(qtyInput.value);
        const existingQty = cart[sr_no] ? cart[sr_no].qty : 0;

        if (!Number.isInteger(qty) || qty <= 0 || existingQty + qty > CommerceCore.MAX_QUANTITY) {
            showToast('Enter a whole-number quantity from 1 to 9,999.');
            return;
        }

        if (cart[sr_no]) {
            cart[sr_no].qty += qty;
        } else {
            const item = readProduct(sr_no, qty, 0);
            if (item.price !== null && (!Number.isFinite(item.price) || item.price < 0)) {
                showToast('This catalog item has an invalid price. Please contact sales.');
                return;
            }
            cart[sr_no] = item;
        }

        qtyInput.value = 1; // reset
        renderCart();
        showToast((cart[sr_no].price === null ? 'Added quote request for ' : 'Added ' + qty + ' × ') + cart[sr_no].name);

        // Auto open cart briefly if it's the first item
        if (Object.keys(cart).length === 1 && !document.getElementById('cartDropdown').classList.contains('open')) {
            toggleCart();
        }
    }

    function updateItemQty(sr_no, change) {
        if (!cart[sr_no]) return;
        cart[sr_no].qty += change;
        if (cart[sr_no].qty <= 0) {
            delete cart[sr_no];
        } else if (cart[sr_no].qty > CommerceCore.MAX_QUANTITY) {
            cart[sr_no].qty = CommerceCore.MAX_QUANTITY;
            showToast('Maximum quantity is 9,999 per item.');
        }
        renderCart();
    }

    function updateItemDiscount(sr_no, value) {
        const discountPct = Number(value);
        if (!Number.isFinite(discountPct) || discountPct < 0 || discountPct > 100) {
            showToast('Item discount must be between 0% and 100%.');
            renderCart();
            return;
        }
        if (!cart[sr_no]) return;
        if (cart[sr_no].price === null) {
            showToast('Discounts can be set after sales confirms the price.');
            return;
        }
        cart[sr_no].discountPct = discountPct;
        renderCart();
    }

    function roundCurrency(amount) {
        return CommerceCore.roundCurrency(amount);
    }

    function getLineAmounts(item) {
        return CommerceCore.calculateLineAmounts(item);
    }

    function formatAmount(amount) {
        return amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function formatRate(rate) {
        return formatAmount(rate).replace(/\.?0+$/, '');
    }

    function getTaxRates() {
        const cgstInput = document.getElementById('cgstRate');
        const sgstInput = document.getElementById('sgstRate');
        if (!cgstInput.checkValidity() || !sgstInput.checkValidity()) return null;

        return {
            cgstRate: cgstInput.valueAsNumber,
            sgstRate: sgstInput.valueAsNumber
        };
    }

    function getTaxBreakdown(subTotal, rates = getTaxRates()) {
        if (!rates) return null;
        const totals = CommerceCore.calculateTotals(Object.keys(cart).map(key => cart[key]), rates);
        return {
            ...totals,
            totalAmount: totals.totalTax
        };
    }

    function displayTaxBreakdown(tax, subTotal) {
        document.getElementById('cgstAmount').innerText = tax ? formatAmount(tax.cgstAmount) : '—';
        document.getElementById('sgstAmount').innerText = tax ? formatAmount(tax.sgstAmount) : '—';
        document.getElementById('totalTaxRate').innerText = tax ? formatRate(tax.totalRate) : '—';
        document.getElementById('taxAmount').innerText = tax ? formatAmount(tax.totalAmount) : '—';
        document.getElementById('grandTotal').innerText = tax ? formatAmount(tax.estimatedTotal) : '—';
        document.getElementById('quoteItemsNote').hidden = !tax || !tax.includesUnpricedItems;
    }

    function saveCart() {
        const snapshot = { version: 1, items: Object.create(null) };
        Object.keys(cart).forEach(sku => {
            snapshot.items[sku] = { qty: cart[sku].qty, discountPct: cart[sku].discountPct };
        });
        const rates = getTaxRates();
        if (rates) snapshot.rates = rates;
        try {
            localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(snapshot));
        } catch (error) {
            console.error('Unable to save the catalog cart in this browser.', error);
            showToast('Cart saved for this page only; browser storage is unavailable.');
        }
    }

    function restoreCart() {
        let raw;
        try {
            raw = localStorage.getItem(CART_STORAGE_KEY);
        } catch (error) {
            console.error('Unable to read the saved catalog cart.', error);
            showToast('Browser storage is unavailable; this cart will not persist after refresh.');
            return;
        }
        if (!raw) return;

        try {
            const validSkus = Object.create(null);
            document.querySelectorAll('.card-title[id^="name-"]').forEach(element => {
                validSkus[element.id.slice(5)] = true;
            });
            const restored = CommerceCore.sanitizeCartSnapshot(JSON.parse(raw), validSkus);
            Object.keys(restored.items).forEach(sku => {
                cart[sku] = readProduct(sku, restored.items[sku].qty, restored.items[sku].discountPct);
            });
            document.getElementById('cgstRate').value = restored.rates.cgstRate;
            document.getElementById('sgstRate').value = restored.rates.sgstRate;
            if (restored.discardedItems) {
                showToast('Unavailable or invalid saved items were removed from the cart.');
            }
        } catch (error) {
            console.error('Unable to restore the saved catalog cart.', error);
            try {
                localStorage.removeItem(CART_STORAGE_KEY);
            } catch (storageError) {
                console.error('Unable to clear the invalid saved catalog cart.', storageError);
            }
            showToast('The saved cart was invalid and has been cleared.');
        }
    }

    function renderCart() {
        const cartItemsDiv = document.getElementById('cartItems');
        cartItemsDiv.replaceChildren();
        let itemsSubtotal = 0;
        let discountTotal = 0;
        let subTotal = 0;
        let totalItems = 0;

        const keys = Object.keys(cart);
        if (keys.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'cart-empty';
            const title = document.createElement('strong');
            title.textContent = 'Your cart is empty';
            emptyState.append(title, document.createTextNode('Add products from the catalog to begin.'));
            cartItemsDiv.appendChild(emptyState);
        } else {
            keys.forEach(k => {
                const item = cart[k];
                const amounts = getLineAmounts(item);
                itemsSubtotal += amounts.gross;
                discountTotal += amounts.discount;
                subTotal += amounts.net;
                totalItems += item.qty;

                const row = document.createElement('div');
                row.className = 'cart-item';
                const details = document.createElement('div');
                const title = document.createElement('div');
                title.className = 'cart-item-title';
                title.textContent = item.name;
                const meta = document.createElement('div');
                meta.className = 'cart-item-meta';
                meta.textContent = [
                    item.size && `Size: ${item.size}`,
                    item.idSize && `ID Size: ${item.idSize}`,
                    item.odSize && `OD Size: ${item.odSize}`,
                    item.lfSize && `L/F Size: ${item.lfSize}`,
                    item.unit && `Unit: ${item.unit}`,
                    item.packing && `Pack: ${item.packing}`
                ].filter(Boolean).join(' · ');
                const rate = document.createElement('div');
                rate.className = 'cart-item-rate';
                rate.textContent = item.price === null
                    ? 'Price on request · seller will confirm'
                    : `Unit price · ₹${formatAmount(item.price)}`;
                const controls = document.createElement('div');
                controls.className = 'cart-qty-controls';
                const decrease = document.createElement('button');
                decrease.className = 'qty-btn';
                decrease.type = 'button';
                decrease.setAttribute('aria-label', `Decrease quantity of ${item.name}`);
                decrease.textContent = '−';
                decrease.addEventListener('click', () => updateItemQty(k, -1));
                const quantity = document.createElement('span');
                quantity.className = 'qty-value';
                quantity.textContent = item.qty;
                const increase = document.createElement('button');
                increase.className = 'qty-btn';
                increase.type = 'button';
                increase.setAttribute('aria-label', `Increase quantity of ${item.name}`);
                increase.textContent = '+';
                increase.addEventListener('click', () => updateItemQty(k, 1));
                controls.append(decrease, quantity, increase);
                details.append(title);
                if (meta.textContent) details.append(meta);
                details.append(rate, controls);
                if (item.price !== null) {
                    const discountDetails = document.createElement('details');
                    discountDetails.className = 'cart-item-discount';
                    discountDetails.open = item.discountOpen;
                    discountDetails.addEventListener('toggle', () => { item.discountOpen = discountDetails.open; });
                    const discountSummary = document.createElement('summary');
                    discountSummary.textContent = item.discountPct > 0 ? `Item discount · ${item.discountPct}%` : 'Add item discount';
                    const discountControls = document.createElement('div');
                    discountControls.className = 'discount-controls';
                    const discountInput = document.createElement('input');
                    discountInput.className = 'discount-input';
                    discountInput.type = 'number';
                    discountInput.min = '0';
                    discountInput.max = '100';
                    discountInput.step = '0.01';
                    discountInput.value = item.discountPct;
                    discountInput.setAttribute('aria-label', `Discount percentage for ${item.name}`);
                    discountInput.addEventListener('change', () => updateItemDiscount(k, discountInput.value));
                    const percentLabel = document.createElement('span');
                    percentLabel.textContent = '% off';
                    discountControls.append(discountInput, percentLabel);
                    discountDetails.append(discountSummary, discountControls);
                    details.append(discountDetails);
                } else {
                    const quoteNote = document.createElement('div');
                    quoteNote.className = 'cart-item-rate';
                    quoteNote.textContent = 'Discount available after price confirmation.';
                    details.append(quoteNote);
                }
                const itemTotal = document.createElement('div');
                itemTotal.className = 'cart-item-total';
                if (amounts.isQuoted) {
                    itemTotal.classList.add('quote-total');
                    itemTotal.textContent = 'Quote required';
                } else {
                    itemTotal.textContent = `₹${formatAmount(amounts.net)}`;
                }
                if (amounts.discount > 0) {
                    const discountNote = document.createElement('span');
                    discountNote.className = 'cart-item-discount-value';
                    discountNote.textContent = `−₹${formatAmount(amounts.discount)}`;
                    itemTotal.appendChild(discountNote);
                }
                row.append(details, itemTotal);
                cartItemsDiv.appendChild(row);
            });
        }

        itemsSubtotal = roundCurrency(itemsSubtotal);
        discountTotal = roundCurrency(discountTotal);
        subTotal = roundCurrency(subTotal);
        document.getElementById('cartCountBadge').innerText = totalItems;

        document.getElementById('itemsSubtotal').innerText = formatAmount(itemsSubtotal);
        document.getElementById('discountTotal').innerText = formatAmount(discountTotal);
        document.getElementById('subTotal').innerText = formatAmount(subTotal);
        displayTaxBreakdown(getTaxBreakdown(subTotal), subTotal);
        document.getElementById('placeOrderButton').disabled = keys.length === 0;
        saveCart();
    }

    function createOrderReference() {
        const now = new Date();
        const date = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'),
            String(now.getDate()).padStart(2, '0')].join('');
        const suffix = Math.floor(Math.random() * 1000000).toString().padStart(6, '0');
        return `SK-${date}-${suffix}`;
    }

    function readBuyerDetails() {
        return {
            name: document.getElementById('buyerName').value,
            phone: document.getElementById('buyerPhone').value,
            email: document.getElementById('buyerEmail').value,
            address: document.getElementById('buyerAddress').value,
            state: document.getElementById('buyerState').value,
            pincode: document.getElementById('buyerPincode').value,
            gstin: document.getElementById('buyerGstin').value
        };
    }

    function sendWhatsAppOrder(order) {
        const sellerPhone = CommerceCore.normalizeIndianMobile(checkoutConfig.dataset.whatsappNumber);
        if (!sellerPhone) {
            throw new Error('The business WhatsApp number is not configured. Please contact sales by phone.');
        }
        const message = CommerceCore.formatOrderMessage(order);
        if (message.length > 4000) {
            throw new Error('This order is too long for a WhatsApp message. Reduce the cart or download the structured order copy.');
        }
        const link = document.getElementById('whatsAppFallback');
        link.href = `https://wa.me/${sellerPhone}?text=${encodeURIComponent(message)}`;
        link.textContent = 'If WhatsApp did not open, continue to send this order request';
        link.hidden = false;
        link.click();
        showToast(`Order ${order.order_reference} prepared. Sales must confirm it; no payment was taken.`);
    }

    async function startPaymentCheckout(order) {
        const apiBaseUrl = checkoutConfig.dataset.apiBaseUrl.trim();
        if (!apiBaseUrl) {
            throw new Error('Online payment is not enabled yet. Your order request has not been charged; contact sales to confirm it.');
        }

        let endpoint;
        try {
            endpoint = new URL('/api/checkout/orders', apiBaseUrl);
        } catch (error) {
            throw new Error('The configured secure checkout API URL is invalid.');
        }
        if (endpoint.protocol !== 'https:') {
            throw new Error('The online checkout API must use HTTPS.');
        }

        const response = await fetch(endpoint.toString(), {
            method: 'POST',
            credentials: 'omit',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(order)
        });
        if (!response.ok) {
            throw new Error(`Secure checkout could not create the order (HTTP ${response.status}). No payment was taken.`);
        }
        const result = await response.json();
        let checkoutUrl;
        try {
            checkoutUrl = new URL(result.checkout_url);
        } catch (error) {
            throw new Error('Secure checkout returned an invalid payment URL. No payment was taken.');
        }
        if (checkoutUrl.protocol !== 'https:') {
            throw new Error('Secure checkout returned a non-HTTPS payment URL. No payment was taken.');
        }
        window.location.assign(checkoutUrl.toString());
    }

    async function placeOrderRequest() {
        if (Object.keys(cart).length === 0) {
            showToast('Add at least one product before requesting an order.');
            return;
        }
        const requiredFields = ['buyerName', 'buyerPhone', 'buyerAddress', 'buyerState', 'buyerPincode'];
        const invalidField = requiredFields.map(id => document.getElementById(id)).find(field => !field.checkValidity());
        if (invalidField) {
            invalidField.reportValidity();
            return;
        }

        const buyer = CommerceCore.validateBuyer(readBuyerDetails());
        if (!buyer.valid) {
            showToast(buyer.errors[0]);
            const target = buyer.errors[0].includes('GSTIN') ? 'buyerGstin'
                : buyer.errors[0].includes('email') ? 'buyerEmail' : 'buyerPhone';
            document.getElementById(target).focus();
            return;
        }
        const rates = getTaxRates();
        if (!rates) {
            showToast('Enter valid CGST and SGST rates before requesting an order.');
            return;
        }

        try {
            lastOrder = CommerceCore.createOrder({
                id: createOrderReference(),
                createdAt: new Date().toISOString(),
                buyer: readBuyerDetails(),
                items: Object.keys(cart).map(key => cart[key]),
                rates
            });
            document.getElementById('orderCopyButton').hidden = false;
            const provider = checkoutConfig.dataset.provider || 'whatsapp';
            if (provider === 'whatsapp') {
                sendWhatsAppOrder(lastOrder);
            } else if (provider === 'razorpay') {
                await startPaymentCheckout(lastOrder);
            } else {
                throw new Error(`Unsupported checkout provider "${provider}". No order or payment was submitted.`);
            }
        } catch (error) {
            console.error('Order request could not be submitted.', error);
            showToast(error.message || 'Order request could not be submitted. Please contact sales.');
        }
    }

    function downloadOrderCopy() {
        if (!lastOrder) {
            showToast('Create an order request before downloading its structured copy.');
            return;
        }
        const blob = new Blob([JSON.stringify(lastOrder, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${lastOrder.order_reference}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    function generateBill() {
        if (Object.keys(cart).length === 0) {
            alert("Cart is empty! Please add items before printing a bill.");
            return;
        }

        const taxRates = getTaxRates();
        if (!taxRates) {
            const invalidInput = [document.getElementById('cgstRate'), document.getElementById('sgstRate')]
                .find(input => !input.checkValidity());
            invalidInput.reportValidity();
            return;
        }

        const buyer = readBuyerDetails();
        const bName = buyer.name.trim() || "Cash customer";
        document.getElementById('pBuyerName').innerText = bName;
        document.getElementById('pBuyerContact').innerText = [buyer.phone.trim(), buyer.email.trim()].filter(Boolean).join(' · ');
        document.getElementById('pBuyerAddress').innerText = [
            buyer.address.trim(), buyer.state, buyer.pincode
        ].filter(Boolean).join(', ');
        document.getElementById('pBuyerGstin').innerText = buyer.gstin.trim()
            ? `Customer GSTIN: ${buyer.gstin.trim().toUpperCase()}` : '';

        const now = new Date();
        const dateStr = now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
        document.getElementById('pDate').innerText = dateStr;
        const dateCode = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('');
        document.getElementById('pInvNo').innerText = `PI-${dateCode}-${String(Math.floor(Math.random() * 1000000)).padStart(6, '0')}`;

        const tbody = document.getElementById('pTableBody');
        tbody.replaceChildren();

        Object.keys(cart).forEach((k, index) => {
            const item = cart[k];
            const amounts = getLineAmounts(item);

            const row = document.createElement('tr');
            const serial = document.createElement('td');
            serial.textContent = index + 1;
            row.appendChild(serial);
            const particulars = document.createElement('td');
            particulars.textContent = item.name;
            const itemName = item.name.toLowerCase();
            const specifications = [];
            if (item.size && !itemName.includes(item.size.toLowerCase())) specifications.push(`Size: ${item.size}`);
            if (item.idSize) specifications.push(`ID Size: ${item.idSize}`);
            if (item.odSize) specifications.push(`OD Size: ${item.odSize}`);
            if (item.lfSize) specifications.push(`L/F Size: ${item.lfSize}`);
            if (item.packing && !itemName.includes(item.packing.toLowerCase())) specifications.push(`Pack: ${item.packing}`);
            if (specifications.length) {
                const detail = document.createElement('div');
                detail.className = 'item-size';
                detail.textContent = specifications.join(' · ');
                particulars.appendChild(detail);
            }
            row.appendChild(particulars);
            const discountDisplay = amounts.isQuoted ? 'Quote' : item.discountPct > 0
                ? `${formatAmount(item.discountPct)}% (₹${formatAmount(amounts.discount)})`
                : '—';
            const rateDisplay = amounts.isQuoted ? 'Quote' : formatAmount(item.price);
            const amountDisplay = amounts.isQuoted ? 'Quote' : formatAmount(amounts.net);
            [item.hsn || '—', item.qty, item.unit || '—', rateDisplay, discountDisplay, amountDisplay].forEach((value, column) => {
                const cell = document.createElement('td');
                cell.textContent = value;
                if ([1, 3, 4, 5].includes(column)) cell.className = 'num';
                row.appendChild(cell);
            });
            tbody.appendChild(row);
        });

        const totals = CommerceCore.calculateTotals(Object.keys(cart).map(key => cart[key]), taxRates);

        document.getElementById('pItemsSubtotal').innerText = formatAmount(totals.itemsSubtotal);
        document.getElementById('pDiscountTotal').innerText = formatAmount(totals.discountTotal);
        document.getElementById('pSubTotal').innerText = formatAmount(totals.taxableSubtotal);
        document.getElementById('pCgstRate').innerText = formatRate(totals.cgstRate);
        document.getElementById('pCgstAmount').innerText = formatAmount(totals.cgstAmount);
        document.getElementById('pSgstRate').innerText = formatRate(totals.sgstRate);
        document.getElementById('pSgstAmount').innerText = formatAmount(totals.sgstAmount);
        document.getElementById('pTaxRate').innerText = formatRate(totals.totalRate);
        document.getElementById('pTaxAmount').innerText = formatAmount(totals.totalTax);
        document.getElementById('pGrandTotal').innerText = formatAmount(totals.estimatedTotal);
        document.getElementById('pQuoteNote').hidden = !totals.includesUnpricedItems;

        window.print();
    }

    restoreCart();
    renderCart();
