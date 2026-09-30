const CommerceCore = window.CatalogCommerce;
const CART_STORAGE_KEY = 'skumar-catalog-cart-v1';
const checkoutConfig = document.getElementById('checkoutConfig');
const billArchive = new CatalogBillArchive.BillArchive({
    window,
    indexedDB: window.indexedDB
});
let cart = Object.create(null);
let lastOrder = null;
let clientRecords = [];
let visibleBills = new Map();
function normalizeSearchText(value) {
    return String(value || '')
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLocaleLowerCase()
        .trim();
}

function parseNumericPrice(listPrice) {
    if (!listPrice) return null;
    const cleaned = String(listPrice).trim().replace(/,/g, '');
    const num = Number(cleaned);
    return (Number.isFinite(num) && num >= 0) ? num : null;
}

const catalogDataElement = document.getElementById('catalogData');
const rawCatalog = catalogDataElement ? JSON.parse(catalogDataElement.textContent) : [];
const catalogSearchIndex = rawCatalog.map((item, index) => ({
    item,
    originalIndex: index,
    numericPrice: parseNumericPrice(item.list_price),
    searchableText: item.search_text || normalizeSearchText([
        item.item_name, item.category, item.hsn_code, item.sr_number,
        item.size,
        item.id_size, item.od_size, item.lf_size
    ].join(' '))
}));

billArchive.restoreDirectory().catch(error => {
    console.error('Unable to restore the generated-bills folder.', error);
});

function renderSavedBills(entries) {
    const list = document.getElementById('billArchiveList');
    list.replaceChildren();
    visibleBills = new Map(entries.map(entry => [entry.id, entry]));
    if (!entries.length) {
        const empty = document.createElement('p');
        empty.className = 'bill-empty';
        empty.textContent = 'No saved bills yet. Print a proforma invoice to archive it.';
        list.appendChild(empty);
        return;
    }

    const byMonth = new Map();
    entries.forEach(entry => {
        if (!byMonth.has(entry.month)) byMonth.set(entry.month, []);
        byMonth.get(entry.month).push(entry);
    });
    byMonth.forEach((monthEntries, month) => {
        const section = document.createElement('details');
        section.className = 'bill-month';
        const summary = document.createElement('summary');
        const monthDate = new Date(`${month}-01T00:00:00Z`);
        summary.textContent = `${monthDate.toLocaleDateString('en-IN', {
            month: 'long',
            year: 'numeric',
            timeZone: 'UTC'
        })} (${monthEntries.length})`;
        section.appendChild(summary);

        const monthList = document.createElement('div');
        monthList.className = 'bill-month-list';
        monthEntries.forEach(entry => {
            const row = document.createElement('div');
            row.className = 'bill-entry';
            const label = document.createElement('div');
            label.className = 'bill-entry-name';
            label.textContent = entry.reference;
            const meta = document.createElement('div');
            meta.className = 'bill-entry-meta';
            meta.textContent = (entry.storage === 'folder' || entry.storage === 'server')
                ? `generated_bills/${entry.month}/${entry.fileName}`
                : 'Saved in this browser archive';
            label.appendChild(meta);
            const btns = document.createElement('div');
            btns.className = 'bill-entry-actions';
            btns.style.display = 'flex';
            btns.style.gap = '8px';
            const open = document.createElement('button');
            open.className = 'bill-open-btn';
            open.type = 'button';
            open.textContent = 'Open';
            open.dataset.billId = entry.id;
            open.dataset.action = 'open';
            
            const printBtn = document.createElement('button');
            printBtn.className = 'bill-open-btn';
            printBtn.type = 'button';
            printBtn.textContent = 'Print';
            printBtn.dataset.billId = entry.id;
            printBtn.dataset.action = 'print';
            
            btns.append(open, printBtn);
            row.append(label, btns);
            monthList.appendChild(row);
        });
        section.appendChild(monthList);
        list.appendChild(section);
    });
}

async function refreshSavedBills() {
    const status = document.getElementById('billArchiveStatus');
    const chooseBtn = document.getElementById('chooseBillsFolderButton');
    status.textContent = 'Loading saved bills...';
    try {
        let entries = [];
        
        if (entries.length === 0) {
            entries = await billArchive.listBills();
            status.textContent = billArchive.directoryHandle
                ? 'Showing bills from the selected folder and this browser archive.'
                : typeof window.showDirectoryPicker === 'function'
                    ? 'Select your generated_bills folder to save and browse its monthly folders.'
                    : 'Folder access is unavailable here; bills are kept in this browser and downloaded.';
            if (chooseBtn && typeof window.showDirectoryPicker === 'function') chooseBtn.style.display = '';
        }
        
        renderSavedBills(entries);
    } catch (error) {
        console.error('Unable to read saved bills.', error);
        status.textContent = error.message || 'Could not read saved bills.';
    }
}

document.getElementById('openBillsButton').addEventListener('click', () => {
    const dialog = document.getElementById('billArchiveDialog');
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    refreshSavedBills();
});
document.getElementById('closeBillArchiveButton').addEventListener('click', () => {
    const dialog = document.getElementById('billArchiveDialog');
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
});
document.getElementById('chooseBillsFolderButton').addEventListener('click', () => {
    const status = document.getElementById('billArchiveStatus');
    status.textContent = 'Choose the generated_bills folder. Monthly folders will be created automatically.';
    try {
        billArchive.selectDirectory().then(() => {
            status.textContent = 'Folder selected. Bills will be saved into monthly subfolders.';
            refreshSavedBills();
        }).catch(error => {
            if (error.name === 'AbortError') {
                status.textContent = 'Folder selection was cancelled.';
                return;
            }
            console.error('Unable to select the generated-bills folder.', error);
            status.textContent = error.message || 'Could not select the generated_bills folder.';
        });
    } catch (error) {
        console.error('Unable to select the generated-bills folder.', error);
        status.textContent = error.message || 'This browser cannot select a local folder.';
    }
});
document.getElementById('billArchiveList').addEventListener('click', event => {
    const button = event.target.closest('button[data-bill-id]');
    if (!button) return;
    const action = button.dataset.action;
    const entry = visibleBills.get(button.dataset.billId);
    if (entry) {
        if (entry.storage === "server") {
            try {
                const order = JSON.parse(entry.order_json);
                cart = order.items || {};
                const buyer = order.buyer || {};
                document.getElementById('buyerName').value = buyer.name || '';
                document.getElementById('buyerPhone').value = buyer.phone || '';
                document.getElementById('buyerEmail').value = buyer.email || '';
                document.getElementById('buyerAddress').value = buyer.address || '';
                if (buyer.state) document.getElementById('buyerState').value = buyer.state;
                if (buyer.pincode) document.getElementById('buyerPincode').value = buyer.pincode;
                if (buyer.gstin) document.getElementById('buyerGstin').value = buyer.gstin;
                
                renderCart();
                document.getElementById('pInvNo').innerText = order.id || entry.reference || '';
                document.getElementById('printBillBtn').style.display = 'block';
                if (action === 'print') {
                    generateBill();
                } else {
                    document.getElementById('billArchiveDialog').close();
                    showToast("Order restored to cart!");
                }
            } catch (e) {
                console.error("Failed to restore bill", e);
                showToast("Failed to restore order from server data.");
            }
        } else {
            billArchive.openBill(entry);
        }
    }
});

function updateCustomerSuggestions(query) {
    const suggestions = document.getElementById('clientSuggestions');
    suggestions.replaceChildren();
    if (!query || !window.ClientDirectory) return;
    const normalizedQuery = query.trim().toLocaleLowerCase();
    clientRecords
        .filter(customer => Object.values(customer).some(value =>
            String(value).toLocaleLowerCase().includes(normalizedQuery)
        ))
        .slice(0, 50)
        .forEach(customer => {
            const option = document.createElement('option');
            option.value = ClientDirectory.displayLabel(customer);
            suggestions.appendChild(option);
        });
}

function applySelectedCustomer(customer) {
    document.getElementById('buyerName').value = customer.business_name || customer.name || '';
    document.getElementById('buyerPhone').value = customer.phone || '';
    document.getElementById('buyerEmail').value = customer.email || '';
    document.getElementById('buyerAddress').value = customer.address || '';
    const stateInput = document.getElementById('buyerState');
    const matchingState = Array.from(stateInput.options).find(option =>
        option.value.toLocaleLowerCase() === (customer.state || '').toLocaleLowerCase()
    );
    stateInput.value = matchingState ? matchingState.value : '';
    document.getElementById('buyerPincode').value = customer.pincode || '';
    document.getElementById('buyerGstin').value = customer.gstin || '';
    document.getElementById('buyerDetails').open = true;
    document.getElementById('clientDirectoryStatus').textContent =
        'Customer details filled in. Review and edit them before submitting the order.';
}

function loadCustomerCsv(file) {
    const status = document.getElementById('clientDirectoryStatus');
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
        status.textContent = 'Customer CSV is larger than 5 MB. Please choose a smaller file.';
        return;
    }
    file.text().then(contents => {
        const records = ClientDirectory.parseCsv(contents);
        clientRecords = records;
        document.getElementById('clientSuggestions').replaceChildren();
        document.getElementById('customerLookup').value = '';
        status.textContent = records.length
            ? `${records.length} customer record${records.length === 1 ? '' : 's'} loaded for this browser session.`
            : 'No customer records found. You can still enter customer details manually.';
    }).catch(error => {
        console.error('Unable to load the customer CSV.', error);
        status.textContent = error.message || 'Could not read this CSV. Check its format and try again.';
    });
}




function setupClientData(records) {
    if (!records || !Array.isArray(records)) records = [];
    clientRecords = records;
    if (window.ClientDirectory) {
        window.ClientDirectory.clients = records;
        if (typeof window.ClientDirectory.renderDataList === "function") window.ClientDirectory.renderDataList();
    }
    var statusEl = document.getElementById('clientDirectoryStatus');
    if (statusEl) {
        statusEl.textContent = records.length
            ? `${records.length} saved customer${records.length === 1 ? '' : 's'} ready to auto-fill.`
            : 'Load data/client_data.csv to auto-fill customers, or enter details manually.';
    }
}

setupClientData(window.INJECTED_CLIENT_DATA || []);

document.getElementById('saveClientButton')?.addEventListener('click', () => {
    const newClient = {
        name: document.getElementById('buyerName').value,
        phone: document.getElementById('buyerPhone').value,
        email: document.getElementById('buyerEmail').value,
        address: document.getElementById('buyerAddress').value,
        state: document.getElementById('buyerState').value,
        pincode: document.getElementById('buyerPincode').value,
        gstin: document.getElementById('buyerGstin').value,
    };
    if (!newClient.name && !newClient.gstin) {
        alert('Please enter a name or GSTIN to save the customer.');
        return;
    }
    
    const statusEl = document.getElementById('clientDirectoryStatus');
    const saveLocally = () => {
        clientRecords.push(newClient);
        setupClientData(clientRecords);
        if (statusEl) {
            statusEl.textContent = 'Customer saved in this browser session. Export/update client_data.csv to keep it permanently.';
        }
    };

    saveLocally();
});

document.getElementById('customerLookup').addEventListener('input', event => {
    updateCustomerSuggestions(event.target.value);
    const selectedCustomer = ClientDirectory.findCustomer(clientRecords, event.target.value);
    if (selectedCustomer) applySelectedCustomer(selectedCustomer);
});

document.getElementById('clientCsvFile')?.addEventListener('change', event => {
    const file = event.target.files && event.target.files[0];
    if (file) loadCustomerCsv(file);
    event.target.value = '';
});

function toggleCart(forceOpen) {
        const drawer = document.getElementById('cartDropdown');
        const isOpen = drawer.classList.contains('open');
        const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : !isOpen;
        drawer.classList.toggle('open', shouldOpen);
        document.getElementById('cartBackdrop').classList.toggle('open', shouldOpen);
        drawer.setAttribute('aria-hidden', String(!shouldOpen));
        document.querySelector('.cart-toggle-btn').setAttribute('aria-expanded', String(shouldOpen));
        document.body.style.overflow = shouldOpen ? 'hidden' : '';
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

    function createCard(item) {
        const card = document.createElement('div');
        card.className = 'card';
        card.dataset.srNumber = item.sr_number;
        
        const imgContainer = document.createElement('div');
        imgContainer.className = 'card-img-container';
        if (item.display_image_path) {
            const img = document.createElement('img');
            img.src = item.display_image_path;
            img.className = 'card-img' + (item.image_is_representative ? ' representative-image' : '');
            img.alt = item.image_is_representative ? 'Representative image for ' + item.category : item.item_name;
            img.loading = 'lazy';
            img.style.cursor = 'zoom-in';
            img.onclick = () => openLightbox(item.sr_number);
            imgContainer.appendChild(img);
        } else {
            const noImg = document.createElement('div');
            noImg.style.cssText = 'color:#aaa; font-size:10px; font-style:italic;';
            noImg.textContent = 'No Image';
            imgContainer.appendChild(noImg);
        }
        card.appendChild(imgContainer);
        
        const content = document.createElement('div');
        content.className = 'card-content';
        const title = document.createElement('p');
        title.className = 'card-title';
        title.id = 'name-' + item.sr_number;
        title.textContent = item.item_name;
        content.appendChild(title);
        
        const meta1 = document.createElement('p');
        meta1.className = 'card-meta';
        meta1.innerHTML = `Sr: ${item.sr_number} | HSN: <span class="hsn-val">${item.hsn_code || ''}</span>`;
        content.appendChild(meta1);
        
        if (item.size && !item.item_name.toLowerCase().includes(item.size.toLowerCase())) {
            const metaSize = document.createElement('p');
            metaSize.className = 'card-meta';
            metaSize.innerHTML = `Size: <span class="size-val">${item.size}</span>`;
            content.appendChild(metaSize);
        }
        
        if (item.id_size || item.od_size || item.lf_size) {
            const metaSizes = document.createElement('p');
            metaSizes.className = 'card-meta';
            const parts = [];
            if (item.id_size) parts.push(`ID Size: <span class="id-size-val">${item.id_size}</span>`);
            if (item.od_size) parts.push(`OD Size: <span class="od-size-val">${item.od_size}</span>`);
            if (item.lf_size) parts.push(`L/F Size: <span class="lf-size-val">${item.lf_size}</span>`);
            metaSizes.innerHTML = parts.join(' · ');
            content.appendChild(metaSizes);
        }
        
        const metaUnit = document.createElement('p');
        metaUnit.className = 'card-meta';
        const unitParts = [];
        if (item.unit) unitParts.push(`Unit: <span class="unit-val">${item.unit}</span>`);
        if (item.packing) unitParts.push(`Pack: <span class="packing-val">${item.packing}</span>`);
        if (unitParts.length) {
            metaUnit.innerHTML = unitParts.join(' · ');
            content.appendChild(metaUnit);
        }
        
        const price = document.createElement('p');
        if (item.list_price) {
            price.className = 'card-price';
            price.innerHTML = `₹<span id="price-${item.sr_number}">${item.list_price}</span>`;
        } else {
            price.className = 'card-price quote-price';
            price.innerHTML = `Price on request<span id="price-${item.sr_number}" hidden></span>`;
        }
        content.appendChild(price);
        card.appendChild(content);
        
        const controls = document.createElement('div');
        controls.className = 'add-controls';
        const qtyInput = document.createElement('input');
        qtyInput.type = 'number';
        qtyInput.id = 'qty-' + item.sr_number;
        qtyInput.className = 'qty-input';
        qtyInput.value = '1';
        qtyInput.min = '1';
        qtyInput.max = '9999';
        qtyInput.step = '1';
        qtyInput.setAttribute('aria-label', `Quantity for ${item.item_name}`);
        
        const addBtn = document.createElement('button');
        addBtn.className = 'add-btn';
        addBtn.textContent = item.list_price ? 'Add' : 'Add to quote';
        addBtn.onclick = () => addToCart(String(item.sr_number));
        
        controls.appendChild(qtyInput);
        controls.appendChild(addBtn);
        card.appendChild(controls);
        
        return card;
    }

function characterOverlap(a, b) {
    if (a.length < 2 || b.length < 2) return 0;
    let matches = 0;
    const bChars = new Set(b.split(''));
    for (const c of a) if (bChars.has(c)) matches++;
    const ratio = matches / Math.max(a.length, b.length);
    return ratio > 0.6 ? ratio * 0.8 : 0;
}

function fuzzyScore(text, query) {
    if (!query) return 1;
    if (!text) return 0;
    if (text.includes(query)) return 1;
    
    const tokens = query.split(/\s+/).filter(Boolean);
    if (!tokens.length) return 1;
    
    let totalScore = 0;
    const words = text.split(/\s+/);
    
    for (const token of tokens) {
        if (text.includes(token)) { totalScore += 1; continue; }
        let bestWordScore = 0;
        for (const word of words) {
            if (word.startsWith(token) || token.startsWith(word)) {
                bestWordScore = Math.max(bestWordScore, 0.9);
            } else {
                const overlap = characterOverlap(token, word);
                bestWordScore = Math.max(bestWordScore, overlap);
            }
        }
        if (bestWordScore < 0.4) return 0;
        totalScore += bestWordScore;
    }
    return totalScore / tokens.length;
}

    function initCategoryPicker() {
        const wrap = document.getElementById('categoryPickerWrap');
        const btn = document.getElementById('categoryPickerBtn');
        const label = document.getElementById('categoryPickerLabel');
        const panel = document.getElementById('categoryDropdownPanel');
        const searchInput = document.getElementById('categorySearchInput');
        const list = document.getElementById('categoryOptionsList');
        const nativeSelect = document.getElementById('categoryFilter');

        if (!wrap || !btn || !panel || !list) return;

        function closePanel() {
            panel.hidden = true;
            btn.setAttribute('aria-expanded', 'false');
            if (searchInput) searchInput.value = '';
            filterCategoryOptions('');
        }

        function openPanel() {
            panel.hidden = false;
            btn.setAttribute('aria-expanded', 'true');
            if (searchInput) {
                searchInput.value = '';
                filterCategoryOptions('');
                setTimeout(() => searchInput.focus(), 60);
            }
        }

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (panel.hidden) {
                openPanel();
            } else {
                closePanel();
            }
        });

        panel.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        document.addEventListener('click', (e) => {
            if (!wrap.contains(e.target)) {
                closePanel();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !panel.hidden) {
                closePanel();
                btn.focus();
            }
        });

        function filterCategoryOptions(query) {
            const q = normalizeSearchText(query);
            const items = list.querySelectorAll('.category-opt-item');
            items.forEach(el => {
                const cat = el.dataset.category || '';
                const nameEl = el.querySelector('.opt-name');
                const name = nameEl ? nameEl.textContent : cat;
                const fullText = normalizeSearchText(cat + ' ' + name);
                const isMatch = !q || fullText.includes(q);
                el.style.display = isMatch ? 'flex' : 'none';
            });
        }

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                filterCategoryOptions(e.target.value);
            });
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    const firstVisible = Array.from(list.querySelectorAll('.category-opt-item')).find(el => el.style.display !== 'none');
                    if (firstVisible) {
                        firstVisible.click();
                        e.preventDefault();
                    }
                }
            });
        }

        list.addEventListener('click', (e) => {
            const itemBtn = e.target.closest('.category-opt-item');
            if (!itemBtn) return;
            const catVal = itemBtn.dataset.category || '';
            selectCategory(catVal);
            closePanel();
        });

        window.selectCategory = function(catVal) {
            if (nativeSelect) nativeSelect.value = catVal;
            const items = list.querySelectorAll('.category-opt-item');
            let selectedName = 'All Categories';
            items.forEach(el => {
                const isMatch = (el.dataset.category || '') === catVal;
                el.classList.toggle('active', isMatch);
                el.setAttribute('aria-selected', isMatch ? 'true' : 'false');
                if (isMatch) {
                    const nameEl = el.querySelector('.opt-name');
                    if (nameEl) selectedName = nameEl.textContent;
                }
            });
            if (label) label.textContent = selectedName;
            filterCatalog();
        };

        if (nativeSelect) {
            nativeSelect.addEventListener('change', () => {
                selectCategory(nativeSelect.value);
            });
        }
    }

    function initCatalogCacheAndPrefs() {
        const currentVersion = document.body.dataset.catalogVersion || 'v1';
        const storedVersion = localStorage.getItem('skumar_catalog_version');

        if (storedVersion && storedVersion !== currentVersion) {
            console.log(`[Cache] Catalog update detected: ${storedVersion} -> ${currentVersion}. Refreshing cache.`);
            localStorage.removeItem('skumar_sort_pref');
            if ('caches' in window) {
                caches.keys().then(names => {
                    names.forEach(name => {
                        if (name.startsWith('skumar-catalog-') && !name.includes(currentVersion)) {
                            caches.delete(name);
                        }
                    });
                });
            }
        }
        localStorage.setItem('skumar_catalog_version', currentVersion);

        const sortSelect = document.getElementById('sortBy');
        if (sortSelect) {
            const savedSort = localStorage.getItem('skumar_sort_pref');
            if (savedSort && ['default', 'price-asc', 'price-desc', 'name-asc'].includes(savedSort)) {
                sortSelect.value = savedSort;
            }
            sortSelect.addEventListener('change', () => {
                localStorage.setItem('skumar_sort_pref', sortSelect.value);
            });
        }
    }

    function filterCatalog() {
        const grid = document.getElementById('catalogGrid');
        if (!grid) return;

        if (catalogSearchIndex.length > 0 && !catalogSearchIndex[0].card) {
            const fragment = document.createDocumentFragment();
            catalogSearchIndex.forEach(entry => {
                entry.card = createCard(entry.item);
                fragment.appendChild(entry.card);
            });
            grid.appendChild(fragment);
        }

        const searchInputEl = document.getElementById('searchInput');
        const input = normalizeSearchText(searchInputEl ? searchInputEl.value : '');
        const categoryFilter = document.getElementById('categoryFilter');
        const selectedCategory = categoryFilter ? categoryFilter.value : '';
        const sortBySelect = document.getElementById('sortBy');
        const sortBy = sortBySelect ? sortBySelect.value : 'default';

        let matchCount = 0;
        const matchingEntries = [];

        catalogSearchIndex.forEach(entry => {
            const matchesCategory = !selectedCategory || entry.item.category === selectedCategory;
            if (!matchesCategory) {
                entry.score = 0;
                entry.card.style.display = 'none';
                return;
            }

            // Empty search + All Categories (or a chosen category) shows every matching product.
            if (input) {
                entry.score = fuzzyScore(entry.searchableText, input);
            } else {
                entry.score = 1;
            }

            if (entry.score >= 0.4) {
                matchCount++;
                entry.card.style.display = 'flex';
                matchingEntries.push(entry);
            } else {
                entry.card.style.display = 'none';
            }
        });

        // Apply sorting to matching items
        if (sortBy === 'price-asc') {
            matchingEntries.sort((a, b) => {
                if (a.numericPrice === null && b.numericPrice === null) return a.originalIndex - b.originalIndex;
                if (a.numericPrice === null) return 1;
                if (b.numericPrice === null) return -1;
                if (a.numericPrice !== b.numericPrice) return a.numericPrice - b.numericPrice;
                return a.originalIndex - b.originalIndex;
            });
        } else if (sortBy === 'price-desc') {
            matchingEntries.sort((a, b) => {
                if (a.numericPrice === null && b.numericPrice === null) return a.originalIndex - b.originalIndex;
                if (a.numericPrice === null) return 1;
                if (b.numericPrice === null) return -1;
                if (a.numericPrice !== b.numericPrice) return b.numericPrice - a.numericPrice;
                return a.originalIndex - b.originalIndex;
            });
        } else if (sortBy === 'name-asc') {
            matchingEntries.sort((a, b) => (a.item.item_name || '').localeCompare(b.item.item_name || ''));
        } else {
            // Default: relevance score when search query is entered, else original catalog order
            if (input) {
                matchingEntries.sort((a, b) => b.score - a.score);
            } else {
                matchingEntries.sort((a, b) => a.originalIndex - b.originalIndex);
            }
        }

        // Single DOM update using DocumentFragment
        const fragment = document.createDocumentFragment();
        matchingEntries.forEach(entry => {
            fragment.appendChild(entry.card);
        });
        grid.appendChild(fragment);

        const countIndicator = document.getElementById('searchResultCount');
        if (countIndicator) {
            let sortLabel = '';
            if (sortBy === 'price-asc') sortLabel = ' · Sorted: Price Low to High';
            else if (sortBy === 'price-desc') sortLabel = ' · Sorted: Price High to Low';
            else if (sortBy === 'name-asc') sortLabel = ' · Sorted: Name A to Z';

            let catLabel = selectedCategory ? ` in "${selectedCategory}"` : ' in All Categories';
            countIndicator.textContent = `Showing ${matchCount} of ${catalogSearchIndex.length} products${catLabel}${sortLabel}`;
        }
    }

    function readProduct(sr_number, qty, discountPct) {
        const row = rawCatalog.find(item => String(item.sr_number) === String(sr_number));
        if (!row) throw new Error('Product not found: ' + sr_number);
        
        const priceText = row.list_price ? String(row.list_price).trim().replace(/,/g, '') : '';
        const parsedPrice = priceText ? Number(priceText) : null;
        
        return {
            sr_number: String(row.sr_number),
            name: row.item_name || '',
            price: parsedPrice,
            qty,
            hsn: row.hsn_code || '',
            size: row.size || '',
            idSize: row.id_size || '',
            odSize: row.od_size || '',
            lfSize: row.lf_size || '',
            unit: row.unit || '',
            packing: row.packing || '',
            discountPct: parsedPrice === null ? 0 : discountPct,
            discountOpen: false
        };
    }

    function addToCart(sr_number) {
        const qtyInput = document.getElementById('qty-' + sr_number);
        const qty = Number(qtyInput.value);
        const existingQty = cart[sr_number] ? cart[sr_number].qty : 0;

        if (!Number.isInteger(qty) || qty <= 0 || existingQty + qty > CommerceCore.MAX_QUANTITY) {
            showToast('Enter a whole-number quantity from 1 to 9,999.');
            return;
        }

        if (cart[sr_number]) {
            cart[sr_number].qty += qty;
        } else {
            const item = readProduct(sr_number, qty, 0);
            if (item.price !== null && (!Number.isFinite(item.price) || item.price < 0)) {
                showToast('This catalog item has an invalid price. Please contact sales.');
                return;
            }
            cart[sr_number] = item;
        }

        qtyInput.value = 1; // reset
        renderCart();
        showToast((cart[sr_number].price === null ? 'Added quote request for ' : 'Added ' + qty + ' × ') + cart[sr_number].name);

        // Auto open cart briefly if it's the first item
        if (Object.keys(cart).length === 1 && !document.getElementById('cartDropdown').classList.contains('open')) {
            toggleCart();
        }
    }

    function updateItemQty(sr_number, change) {
        if (!cart[sr_number]) return;
        cart[sr_number].qty += change;
        if (cart[sr_number].qty <= 0) {
            delete cart[sr_number];
        } else if (cart[sr_number].qty > CommerceCore.MAX_QUANTITY) {
            cart[sr_number].qty = CommerceCore.MAX_QUANTITY;
            showToast('Maximum quantity is 9,999 per item.');
        }
        renderCart();
    }

    function updateItemDiscount(sr_number, value) {
        const discountPct = Number(value);
        if (!Number.isFinite(discountPct) || discountPct < 0 || discountPct > 100) {
            showToast('Item discount must be between 0% and 100%.');
            renderCart();
            return;
        }
        if (!cart[sr_number]) return;
        if (cart[sr_number].price === null) {
            showToast('Discounts can be set after sales confirms the price.');
            return;
        }
        cart[sr_number].discountPct = discountPct;
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
            rawCatalog.forEach(item => {
                validSkus[String(item.sr_number)] = true;
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
        document.getElementById('orderSummaryCount').textContent =
            `${keys.length} item${keys.length === 1 ? '' : 's'}`;
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
                let rate = document.createElement('div');
                rate.className = 'cart-item-rate';
                if (item.price === null) {
                    rate.classList.add('quote-edit-container');
                    rate.style.display = 'flex';
                    rate.style.alignItems = 'center';
                    rate.style.gap = '8px';
                    rate.innerHTML = '<label style="font-size: 0.8em; margin-right: 4px;">Quote Rate (\u20B9): </label><input type="number" class="quote-price-input" min="0" step="0.01" placeholder="Enter rate" style="width: 80px; padding: 2px;">';
                    const input = rate.querySelector('input');
                    if (item.customPrice !== undefined) {
                        input.value = item.customPrice;
                    }
                    input.addEventListener('change', (e) => {
                        const val = parseFloat(e.target.value);
                        if (!isNaN(val) && val >= 0) {
                            item.customPrice = val;
                        } else {
                            delete item.customPrice;
                        }
                        saveCart();
                        renderCart();
                    });
                } else {
                    rate.textContent = `Unit price \u2022 \u20B9${formatAmount(item.price)}`;
                }
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

        const itemsSubtotalEl = document.getElementById('itemsSubtotal');
        if (itemsSubtotalEl) itemsSubtotalEl.innerText = formatAmount(itemsSubtotal);
        const itemsSubtotalSummaryEl = document.getElementById('itemsSubtotalSummary');
        if (itemsSubtotalSummaryEl) itemsSubtotalSummaryEl.innerText = formatAmount(itemsSubtotal);
        document.getElementById('discountTotal').innerText = formatAmount(discountTotal);
        document.getElementById('subTotal').innerText = formatAmount(subTotal);
        displayTaxBreakdown(getTaxBreakdown(subTotal), subTotal);
        const pob = document.getElementById('placeOrderButton'); if (pob) pob.disabled = keys.length === 0;
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
            gstin: document.getElementById('buyerGstin').value,
            deliveryInstructions: (document.getElementById('deliveryInstructions') || {}).value || '',
            transportPreference: (document.getElementById('transportPreference') || {}).value || ''
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
        const requiredFields = ['buyerName', 'buyerPhone'];
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

    function standaloneBillHtml() {
        const stylesheet = Array.from(document.styleSheets).find(sheet =>
            sheet.href && sheet.href.includes('search_catalog.css')
        );
        if (!stylesheet) throw new Error('The invoice stylesheet is unavailable; the bill was not archived.');

        let css;
        try {
            css = Array.from(stylesheet.cssRules, rule => rule.cssText).join('\n');
        } catch (error) {
            throw new Error('The invoice styling could not be embedded for the saved bill.');
        }
        const reference = document.getElementById('pInvNo').innerText.trim();
        const safeTitle = reference.replace(/[<>&"']/g, character => ({
            '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;'
        }[character]));
        const screenStyles = `
            @media screen {
                body { min-height: 100vh; margin: 0; padding: 18px; box-sizing: border-box; background: #f5f7fa; }
                #printBill { display: block !important; position: static; inset: auto; width: min(100%, 1000px); margin: 18px auto; padding: 24px; box-sizing: border-box; background: #fff; box-shadow: 0 8px 28px rgba(15,23,42,.12); }
                #printBill * { box-sizing: border-box; }
                .inv-topline { height: 5px; margin-bottom: 18px; background: #173b57; }
                .inv-header { display: flex; justify-content: space-between; gap: 20px; padding-bottom: 16px; margin-bottom: 18px; border-bottom: 1px solid #cbd5e1; }
                .inv-brand { min-width: 0; }
                .inv-brand h1 { margin: 0 0 5px; color: #173b57; font-size: 24px; }
                .inv-brand p { margin: 3px 0; color: #486581; font-size: 12px; line-height: 1.45; }
                .inv-brand .legal-name { font-size: 11px; font-weight: 700; letter-spacing: .08em; }
                .inv-brand .inv-contact { font-size: 10px; }
                .inv-title { flex: 0 0 auto; min-width: 150px; text-align: right; }
                .inv-title h2 { margin: 0 0 7px; color: #173b57; font-size: 21px; }
                .inv-title span, .inv-fact span:first-child { color: #627d98; }
                .inv-meta { display: grid; grid-template-columns: 1.4fr 1fr; gap: 14px; margin-bottom: 20px; }
                .inv-card { padding: 12px; background: #f4f7fa; border: 1px solid #d9e2ec; border-radius: 4px; }
                .inv-card-label { margin-bottom: 8px; color: #627d98; font-size: 11px; font-weight: 700; text-transform: uppercase; }
                .inv-buyer { margin-bottom: 4px; color: #172b4d; font-weight: 700; }
                .inv-buyer-detail { color: #486581; font-size: 12px; line-height: 1.5; white-space: pre-line; overflow-wrap: anywhere; }
                .inv-facts { display: grid; gap: 9px; }
                .inv-fact { display: flex; justify-content: space-between; gap: 14px; font-size: 12px; }
                table.inv-table, .inv-summary table { width: 100%; border-collapse: collapse; }
                .inv-table th, .inv-table td { padding: 7px 5px; border-bottom: 1px solid #d9e2ec; font-size: 11px; text-align: left; }
                .inv-table th { background: #173b57; color: #fff; }
                .inv-table td.num, .inv-table th.num, .inv-summary td.num { text-align: right; white-space: nowrap; }
                .inv-summary { width: min(360px, 100%); margin: 18px 0 0 auto; }
                .inv-summary td { padding: 7px 8px; border-bottom: 1px solid #e2e8f0; font-size: 12px; }
                .inv-summary .total td { padding-top: 11px; border-top: 2px solid #173b57; color: #173b57; font-size: 15px; font-weight: 700; }
                .inv-notes { margin-top: 24px; padding-top: 12px; border-top: 1px solid #d9e2ec; color: #627d98; font-size: 11px; line-height: 1.5; }
                .inv-signoff { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-top: 28px; color: #627d98; font-size: 11px; }
                .inv-signature { width: 190px; padding-top: 7px; border-top: 1px solid #829ab1; text-align: center; }
                .inv-footer { margin-top: 16px; color: #829ab1; font-size: 10px; text-align: center; }
            }
            @media screen and (max-width: 600px) {
                body { padding: 8px; }
                #printBill { margin: 0 auto; padding: 12px; overflow-x: auto; }
                .inv-header { flex-direction: column; gap: 12px; }
                .inv-title { text-align: left; }
                .inv-meta { grid-template-columns: 1fr; gap: 8px; }
                .inv-table { min-width: 700px; }
                .inv-signoff { align-items: flex-start; flex-direction: column; }
            }
        `;
        return `<!doctype html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proforma invoice ${safeTitle}</title>
    <style>${css.replace(/<\/style/gi, '<\\/style')}</style>
    <style>${screenStyles}</style>
    </head>
    <body>${document.getElementById('printBill').outerHTML}</body>
    </html>`;
    }

    function archiveCurrentBill(date) {
        const reference = document.getElementById('pInvNo').innerText.trim();
        const html = standaloneBillHtml();
        
        return billArchive.saveBill({ date, reference, html });
    }

        async function saveBillRequest() {
        if (Object.keys(cart).length === 0) {
            alert("Cart is empty! Please add items before saving a bill.");
            return;
        }
        const taxRates = getTaxRates();
        if (!taxRates) {
            const invalidInput = [document.getElementById('cgstRate'), document.getElementById('sgstRate')]
                .find(input => !input.checkValidity());
            if (invalidInput) invalidInput.reportValidity();
            return;
        }
        const now = new Date();
        const reference = document.getElementById('pInvNo').innerText.trim() || '';

        const order = CommerceCore.createOrder({
            id: reference,
            createdAt: now.toISOString(),
            buyer: readBuyerDetails(),
            items: cart,
            totals: {
                subTotal: getSubTotal(),
                grandTotal: getSubTotal() + Object.values(getTaxBreakdown(getSubTotal())).reduce((a, b) => a + b, 0)
            }
        });



        // Static Pages / offline: prepare proforma and archive with File System Access / download
        generateBill({ printAfter: false });
    }

    function generateBill(options = {}) {
        const printAfter = options.printAfter !== false;
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

        const printBill = () => window.print();
        const finishWithoutPrint = () => {
            document.getElementById('printBillBtn').style.display = 'block';
        };
        try {
            archiveCurrentBill(now).then(result => {
                const message = result.storage === 'folder'
                    ? `Saved ${result.entry.fileName} in generated_bills/${result.entry.month}/.`
                    : result.storage === 'browser'
                        ? `Saved ${result.entry.fileName} in this browser and downloaded a copy.`
                        : `Downloaded ${result.entry.fileName}; browser storage is unavailable.`;
                document.getElementById('billArchiveStatus').textContent = message;
                showToast(message);
                finishWithoutPrint();
                if (result.entry.archiveWarning) {
                    document.getElementById('billArchiveStatus').textContent +=
                        ` Archive detail: ${result.entry.archiveWarning}`;
                }
            }).catch(error => {
                if (error.name === 'AbortError') {
                    document.getElementById('billArchiveStatus').textContent = 'Bill save: Folder selection cancelled.';
                    finishWithoutPrint();
                    return;
                }
                console.error('The proforma invoice could not be archived.', error);
                const message = `Bill prepared but not saved: ${error.message || 'archive error'}`;
                document.getElementById('billArchiveStatus').textContent = message;
                showToast(message);
                finishWithoutPrint();
            }).finally(() => {
                if (printAfter) printBill();
            });
        } catch (error) {
            console.error('The proforma invoice could not be prepared for archiving.', error);
            document.getElementById('billArchiveStatus').textContent =
                `Bill prepared but not saved: ${error.message || 'archive error'}`;
            finishWithoutPrint();
            if (printAfter) printBill();
        }
    }

    initCatalogCacheAndPrefs();
    initCategoryPicker();
    restoreCart();
    renderCart();

    // Deep link from photo catalog: index.html?category=Capacitors
    const categoryParam = new URLSearchParams(location.search).get('category');
    if (categoryParam && typeof window.selectCategory === 'function') {
        const nativeSelect = document.getElementById('categoryFilter');
        const hasOption = nativeSelect && Array.from(nativeSelect.options).some(
            opt => opt.value === categoryParam
        );
        if (hasOption) {
            window.selectCategory(categoryParam);
        } else {
            filterCatalog();
        }
    } else {
        filterCatalog();
    }


// Lightbox logic
let lightboxDialog = document.getElementById('imageLightbox');
if (!lightboxDialog) {
    lightboxDialog = document.createElement('dialog');
    lightboxDialog.id = 'imageLightbox';
    lightboxDialog.style.cssText = 'padding:0; border:none; border-radius:8px; background:transparent; max-width:90vw; max-height:90vh; overflow:visible;';
    lightboxDialog.innerHTML = `
        <form method="dialog" style="display:flex; flex-direction:column; align-items:center; position:relative; background:white; border-radius:12px; overflow:hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
            <button type="button" onclick="this.closest('dialog').close()" style="position:absolute; top:15px; right:15px; width:36px; height:36px; border-radius:50%; background:#f1f5f9; color:#0f172a; border:none; cursor:pointer; font-weight:bold; font-size:16px; z-index:10; display:flex; align-items:center; justify-content:center; transition: background 0.2s;">✕</button>
            <div style="background:#f8fafc; width:100%; text-align:center; padding: 20px; border-bottom:1px solid #e2e8f0;">
                <img id="lightboxImg" style="max-width:90vw; max-height:60vh; object-fit:contain; border-radius:8px;" src="" alt="Large">
            </div>
            <div style="padding: 20px; width:100%; text-align:left; box-sizing:border-box;">
                <h3 id="lightboxTitle" style="margin:0 0 10px 0; font-size:20px; color:#1e293b;"></h3>
                <p id="lightboxPrice" style="margin:0 0 15px 0; font-size:18px; color:#10b981; font-weight:bold;"></p>
                <div style="display:flex; gap:10px; align-items:center;">
                    <input type="number" id="lightboxQty" value="1" min="1" max="9999" style="width:70px; padding:10px; border:1px solid #cbd5e1; border-radius:6px; font-size:16px;">
                    <button type="button" id="lightboxAddBtn" style="flex:1; background:#2563eb; color:white; border:none; padding:12px 20px; border-radius:6px; font-size:16px; font-weight:bold; cursor:pointer; transition: background 0.2s;">Add to Cart</button>
                </div>
            </div>
        </form>
    `;
    lightboxDialog.addEventListener('click', (e) => {
        if(e.target === lightboxDialog) lightboxDialog.close();
    });
    document.body.appendChild(lightboxDialog);
}

function openLightbox(srNumber) {
    const entry = catalogSearchIndex.find(e => e.item.sr_number === srNumber);
    if (!entry) return;
    const item = entry.item;
    
    document.getElementById('lightboxImg').src = item.display_image_path || '';
    document.getElementById('lightboxImg').alt = item.item_name || 'Product image';
    document.getElementById('lightboxTitle').textContent = item.item_name;
    document.getElementById('lightboxPrice').textContent = item.list_price ? `₹${item.list_price}` : 'Price on request';
    document.getElementById('lightboxQty').value = document.getElementById('qty-' + srNumber) ? document.getElementById('qty-' + srNumber).value : 1;
    
    const addBtn = document.getElementById('lightboxAddBtn');
    addBtn.onclick = () => {
        const qty = parseInt(document.getElementById('lightboxQty').value) || 1;
        addToCart(item, qty);
        lightboxDialog.close();
    };
    
    lightboxDialog.showModal();
}

