(function () {
    'use strict';

    // The seller API only runs on port 8766 (local_seller.py).
    // Auto-redirect if this page was opened from any other port.
    if (location.port !== '8766' && (location.hostname === '127.0.0.1' || location.hostname === 'localhost')) {
        location.href = 'http://127.0.0.1:8766' + location.pathname + location.search;
        return;
    }

    var endpoint = '/api/';
    var fields = [];
    var rows = [];
    var revision = '';
    var editingSerial = null;
    var undoDrafts = [];
    var savedUndoAvailable = false;
    var draftKey = 'skumar-seller-draft-v1';
    var status = document.getElementById('sellerStatus');
    var undoButton = document.getElementById('sellerUndoButton');
    var editorDialog = document.getElementById('sellerEditorDialog');
    var editorForm = document.getElementById('sellerEditorForm');
    var editorFields = document.getElementById('sellerEditorFields');

    function request(path, payload) {
        var options = {
            method: payload ? 'POST' : 'GET',
            cache: 'no-store',
            headers: { Accept: 'application/json' }
        };
        if (payload) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(payload);
        }
        return fetch(endpoint + path, options).then(function (response) {
            return response.text().then(function(text) {
                var data;
                try { data = JSON.parse(text); } catch(e) {}
                if (!response.ok) {
                    throw new Error(data && data.error ? data.error : ('Local seller API failed (' + response.status + '). Ensure start_seller.bat is running.'));
                }
                if (!data) throw new Error('Received an invalid response from the seller server.');
                return data;
            });
        });
            });
        });
    }

    function setCatalog(data) {
        fields = data.fields;
        rows = data.rows;
        revision = data.revision;
        undoDrafts = [];
        savedUndoAvailable = false;
        updateUndoButton();
    }

    function restoreDraft(data) {
        var serialized = window.sessionStorage.getItem(draftKey);
        if (!serialized) return false;
        var draft = JSON.parse(serialized);
        if (draft.revision !== data.revision || !Array.isArray(draft.rows)) {
            window.sessionStorage.removeItem(draftKey);
            return false;
        }
        rows = draft.rows;
        undoDrafts = Array.isArray(draft.undoDrafts) ? draft.undoDrafts : [];
        updateUndoButton();
        return true;
    }

    function updateUndoButton() {
        undoButton.disabled = undoDrafts.length === 0 && !savedUndoAvailable;
    }

    function pushDraftUndo() {
        undoDrafts.push(JSON.stringify(rows));
        if (undoDrafts.length > 30) undoDrafts.shift();
        updateUndoButton();
    }

    function reloadPage() {
        window.location.reload();
    }

    function rowForSerial(serial) {
        return rows.find(function (row) { return String(row.sr_number) === String(serial); });
    }

    function textElement(parent, tag, className, text) {
        var element = document.createElement(tag);
        if (className) element.className = className;
        element.textContent = text || '';
        parent.appendChild(element);
        return element;
    }

    function renderDraft() {
        var grid = document.getElementById('catalogGrid');
        try {
            grid.innerHTML = '';
            rows.forEach(function (row) {
            var card = document.createElement('div');
            card.className = 'card' + (row.hidden ? ' seller-hidden-item' : '');
            card.dataset.srNumber = row.sr_number;
            card.dataset.category = row.category;
            card.dataset.search = [
                row.item_name, row.category, row.hsn_code, row.sr_number,
                row.size,
                row.id_size, row.od_size, row.lf_size
            ].join(' ').toLocaleLowerCase();

            var imageContainer = textElement(card, 'div', 'card-img-container', '');
            var imagePath = row.display_image_path;
            if (imagePath) {
                var image = document.createElement('img');
                image.className = 'card-img' + (row.image_is_representative ? ' representative-image' : '');
                image.src = imagePath;
                image.alt = row.image_is_representative ? 'Representative image for ' + row.category : row.item_name;
                image.loading = 'lazy';
                imageContainer.appendChild(image);
            } else {
                textElement(imageContainer, 'span', '', 'No image');
            }

            var content = textElement(card, 'div', 'card-content', '');
            textElement(content, 'p', 'card-title', row.item_name);
            textElement(
                content,
                'p',
                'card-meta',
                'ID: ' + row.sr_number + ' | HSN: '
                    + (row.hsn_code || '')
            );
            [
                ['Size', row.size],
                ['ID Size', row.id_size],
                ['OD Size', row.od_size],
                ['L/F Size', row.lf_size],
                ['Unit', row.unit],
                ['Pack', row.packing]
            ].forEach(function (pair) {
                if (pair[1]) textElement(content, 'p', 'card-meta', pair[0] + ': ' + pair[1]);
            });
            var price = textElement(
                content,
                'p',
                row.list_price ? 'card-price' : 'card-price quote-price',
                row.list_price ? '₹' + row.list_price : 'Price on request'
            );
            price.dataset.listPrice = row.list_price || '';
            var editIcon = document.createElement('span');
            editIcon.innerHTML = ' ✏️';
            editIcon.style.cursor = 'pointer';
            editIcon.style.fontSize = '12px';
            editIcon.dataset.quickEditSerial = row.sr_number;
            price.appendChild(editIcon);

            var controls = textElement(card, 'div', 'add-controls', '');
            if (row.hidden) textElement(controls, 'span', 'seller-hidden-label', 'Hidden from customers');
            [
                ['Edit', 'seller-item-edit', 'editSerial'],
                [row.hidden ? 'Show' : 'Hide', 'seller-item-hide', 'hideSerial'],
                ['Delete', 'seller-item-delete', 'deleteSerial']
            ].forEach(function (control) {
                var button = textElement(controls, 'button', control[1], control[0]);
                button.type = 'button';
                button.dataset[control[2]] = row.sr_number;
            });
            grid.appendChild(card);
        });
        } catch (err) {
            status.textContent = 'Render Error: ' + err.message;
            console.error(err);
        }
    }

    function fieldLabel(field) {
        return field.replace(/_/g, ' ').replace(/\b\w/g, function (letter) {
            return letter.toUpperCase();
        });
    }

    function buildEditor(row, isNew) {
        editorFields.innerHTML = '';
        fields.forEach(function (field) {
            var wrapper = document.createElement('div');
            wrapper.className = 'seller-field' + (
                ['item_name', 'category', 'packing', 'notes'].includes(field)
                    ? ' seller-field-wide' : ''
            );
            var label = document.createElement('label');
            label.htmlFor = 'seller-field-' + field;
            label.textContent = fieldLabel(field);
            var input = ['item_name', 'category', 'notes'].includes(field)
                ? document.createElement('textarea')
                : document.createElement('input');
            input.id = 'seller-field-' + field;
            input.name = field;
            input.value = row[field] || '';
            input.required = ['sr_number', 'category', 'item_name'].includes(field);
            if (field === 'sr_number') {
                input.inputMode = 'numeric';
            }
            if (field === 'list_price') input.inputMode = 'decimal';
            if (isNew && field === 'hidden') input.value = '';
            wrapper.appendChild(label);
            wrapper.appendChild(input);
            editorFields.appendChild(wrapper);
        });
        document.getElementById('sellerEditorTitle').textContent =
            isNew ? 'Add catalog item' : 'Edit Sr. ' + row.sr_number;
        editorDialog.showModal();
        var firstEditable = editorFields.querySelector(
            'input:not([readonly]):not([disabled]),textarea:not([readonly]):not([disabled])'
        );
        if (firstEditable) firstEditable.focus();
    }

    function draftNewRow() {
        var row = {};
        fields.forEach(function (field) { row[field] = ''; });
        
        var category = 'New category';
        var sameCategory = rows.filter(function (item) { return item.category === category; });
        var nextGroup, nextItem;
        
        if (sameCategory.length) {
            var parts = String(sameCategory[0].sr_number).split('.');
            nextGroup = parts[0] || '1';
            nextItem = String(Math.max.apply(null, sameCategory.map(function (item) {
                var p = String(item.sr_number).split('.');
                return Number(p[1]) || 0;
            })) + 1);
        } else {
            nextGroup = String(Math.max.apply(null, [0].concat(rows.map(function (item) {
                var p = String(item.sr_number).split('.');
                return Number(p[0]) || 0;
            }))) + 1);
            nextItem = '1';
        }
        
        row.sr_number = nextGroup + '.' + nextItem;
        row.category = category;
        row.hidden = '';
        return row;
    }

    document.getElementById('sellerAddButton').addEventListener('click', function () {
        editingSerial = null;
        buildEditor(draftNewRow(), true);
    });

    editorForm.addEventListener('submit', function (event) {
        event.preventDefault();
        var formData = new FormData(editorForm);
        var updated = {};
        fields.forEach(function (field) {
            updated[field] = String(formData.get(field) || '').trim();
        });
        pushDraftUndo();
        if (editingSerial === null) {
            rows.push(updated);
        } else {
            var index = rows.findIndex(function (row) {
                return String(row.sr_number) === String(editingSerial);
            });
            if (index < 0) {
                status.textContent = 'That product is no longer in the local draft.';
                return;
            }
            rows[index] = updated;
        }
        editorDialog.close();
        saveDraft();
        renderDraft();
        status.textContent = 'Unsaved changes are in this page draft. Save & run updater to write them to the CSV.';
    });

    document.getElementById('sellerEditorClose').addEventListener('click', function () {
        editorDialog.close();
    });
    document.getElementById('sellerEditorCancel').addEventListener('click', function () {
        editorDialog.close();
    });

    document.getElementById('sellerUndoButton').addEventListener('click', function () {
        if (undoDrafts.length) {
            rows = JSON.parse(undoDrafts.pop());
            saveDraft();
            updateUndoButton();
            status.textContent = 'Last unsaved page change was undone.';
            renderDraft();
            return;
        }
        request('catalog/undo', { revision: revision }).then(function (data) {
            setCatalog(data);
            window.sessionStorage.removeItem(draftKey);
            status.textContent = data.message;
            window.setTimeout(reloadPage, 500);
        }).catch(function (error) {
            status.textContent = error.message;
        });
    });

    function enableQuickPriceEdit(priceElem, srNumber) {
        var currentPrice = priceElem.dataset.listPrice || '';
        var input = document.createElement('input');
        input.type = 'number';
        input.step = '0.01';
        input.value = currentPrice;
        input.style.width = '80px';
        input.style.padding = '2px 4px';
        input.style.fontSize = '14px';

        var restorePriceDisplay = function (newPrice) {
            priceElem.className = newPrice ? 'card-price' : 'card-price quote-price';
            priceElem.textContent = newPrice ? '₹' + newPrice : 'Price on request';
            priceElem.dataset.listPrice = newPrice;
            var editIcon = document.createElement('span');
            editIcon.innerHTML = ' ✏️';
            editIcon.style.cursor = 'pointer';
            editIcon.style.fontSize = '12px';
            editIcon.dataset.quickEditSerial = srNumber;
            priceElem.appendChild(editIcon);
        };

        var finishEdit = function () {
            if (input.dataset.saved) return;
            input.dataset.saved = 'true';
            var newPrice = input.value.trim();
            pushDraftUndo();
            var editRow = rowForSerial(srNumber);
            if (editRow) {
                editRow.list_price = newPrice;
                saveDraft();
                restorePriceDisplay(newPrice);
                status.textContent = 'Price updated in draft. Save to persist.';
                var toast = document.getElementById('toast');
                if (toast) {
                    toast.textContent = 'Price updated to ' + (newPrice ? '₹' + newPrice : 'Price on request');
                    toast.classList.add('show');
                    setTimeout(function() { toast.classList.remove('show'); }, 3000);
                }
            } else {
                restorePriceDisplay(currentPrice);
            }
        };

        input.addEventListener('blur', finishEdit);
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') finishEdit();
            if (e.key === 'Escape') {
                input.dataset.saved = 'true';
                restorePriceDisplay(currentPrice);
            }
        });

        priceElem.innerHTML = '';
        priceElem.appendChild(input);
        input.focus();
    }

    document.getElementById('catalogGrid').addEventListener('click', function (event) {
        var target = event.target;
        if (!target || !target.dataset) return;
        if (target.dataset.quickEditSerial) {
            enableQuickPriceEdit(target.parentElement, target.dataset.quickEditSerial);
            return;
        }
        if (target.dataset.editSerial) {
            var editRow = rowForSerial(target.dataset.editSerial);
            if (!editRow) return;
            editingSerial = editRow.sr_number;
            buildEditor(editRow, false);
            return;
        }
        if (target.dataset.hideSerial) {
            var hideRow = rowForSerial(target.dataset.hideSerial);
            if (!hideRow) return;
            pushDraftUndo();
            hideRow.hidden = hideRow.hidden ? '' : 'true';
            status.textContent = 'Visibility change is unsaved. Hidden items remain in seller data and will be excluded from customer pages.';
            saveDraft();
            renderDraft();
            return;
        }
        if (target.dataset.deleteSerial) {
            var serial = target.dataset.deleteSerial;
            if (!window.confirm('Delete Sr. ' + serial + ' from the catalog? You can undo before saving.')) return;
            pushDraftUndo();
            rows = rows.filter(function (row) { return String(row.sr_number) !== String(serial); });
            status.textContent = 'Product removed from the unsaved draft. Save to persist, or Undo to restore it.';
            saveDraft();
            renderDraft();
        }
    });

    function saveDraft() {
        window.sessionStorage.setItem(draftKey, JSON.stringify({
            revision: revision,
            rows: rows,
            undoDrafts: undoDrafts
        }));
    }

    // Expose filterCatalog globally for the HTML oninput handler
    window.filterCatalog = function() {
        var input = document.getElementById('searchInput').value.toLocaleLowerCase().trim();
        var categoryFilter = document.getElementById('categoryFilter');
        var selectedCategory = categoryFilter ? categoryFilter.value : '';
        
        var grid = document.getElementById('catalogGrid');
        var cards = grid.getElementsByClassName('card');
        for (var i = 0; i < cards.length; i++) {
            var card = cards[i];
            var searchData = card.dataset.search || '';
            var matchesSearch = searchData.includes(input);
            var matchesCategory = !selectedCategory || card.dataset.category === selectedCategory;
            card.style.display = (matchesSearch && matchesCategory) ? 'flex' : 'none';
        }
    };

    document.getElementById('sellerSaveButton').addEventListener('click', function () {
        var button = document.getElementById('sellerSaveButton');
        button.disabled = true;
        status.textContent = 'Saving CSV, rebuilding catalogs, and running the one-click updater checks…';
        request('catalog/save', { revision: revision, rows: rows }).then(function (data) {
            setCatalog(data);
            window.sessionStorage.removeItem(draftKey);
            status.textContent = data.message;
            window.setTimeout(reloadPage, 800);
        }).catch(function (error) {
            status.textContent = error.message;
            button.disabled = false;
        });
    });

    request('catalog').then(function (data) {
        setCatalog(data);
        var restoredDraft = restoreDraft(data);
        renderDraft();
        status.textContent = 'Connected to the loopback-only seller editor. ' + rows.length + ' products loaded.'
            + (restoredDraft ? ' Unsaved draft restored.' : '');
        request('undo/status').then(function (undo) {
            savedUndoAvailable = undo.can_undo;
            updateUndoButton();
            status.textContent += undo.can_undo ? ' Saved changes can be undone.' : '';
        }).catch(function () {});
    }).catch(function (error) {
        document.getElementById('sellerAddButton').disabled = true;
        document.getElementById('sellerSaveButton').disabled = true;
        status.textContent = error.message + ' Start tools/seller/start_seller.bat.';
    });
}());
