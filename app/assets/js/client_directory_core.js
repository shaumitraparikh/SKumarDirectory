(function (root, factory) {
    const directory = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = directory;
    } else {
        root.ClientDirectory = directory;
    }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    const FIELD_ALIASES = {
        client_id: ['client_id', 'customer_id', 'id', 'code'],
        name: ['name', 'customer_name', 'contact_name', 'contact_person'],
        business_name: ['business_name', 'company', 'company_name', 'business'],
        phone: ['phone', 'mobile', 'mobile_number', 'whatsapp', 'whatsapp_number'],
        email: ['email', 'email_address'],
        address: ['address', 'delivery_address', 'street_address'],
        state: ['state', 'state_ut', 'province'],
        pincode: ['pincode', 'pin', 'pin_code', 'postal_code', 'zip'],
        gstin: ['gstin', 'gst_number', 'tax_id']
    };

    function parseCsv(text) {
        const rows = [];
        let row = [];
        let field = '';
        let quoted = false;

        for (let index = 0; index < text.length; index += 1) {
            const character = text[index];
            if (quoted) {
                if (character === '"' && text[index + 1] === '"') {
                    field += '"';
                    index += 1;
                } else if (character === '"') {
                    quoted = false;
                } else {
                    field += character;
                }
            } else if (character === '"' && field.length === 0) {
                quoted = true;
            } else if (character === ',') {
                row.push(field);
                field = '';
            } else if (character === '\n' || character === '\r') {
                if (character === '\r' && text[index + 1] === '\n') index += 1;
                row.push(field);
                if (row.some(value => value.trim())) rows.push(row);
                row = [];
                field = '';
            } else {
                field += character;
            }
        }

        if (quoted) throw new Error('Customer CSV contains an unclosed quoted field.');
        row.push(field);
        if (row.some(value => value.trim())) rows.push(row);
        if (rows.length < 2) return [];

        const headers = rows.shift().map((header, index) =>
            (index === 0 ? header.replace(/^\uFEFF/, '') : header).trim().toLowerCase()
                .replace(/[\s-]+/g, '_')
        );
        return rows.map(values => {
            const record = {};
            headers.forEach((header, index) => {
                const value = (values[index] || '').trim();
                const fieldNames = Object.keys(FIELD_ALIASES);
                for (let fieldIndex = 0; fieldIndex < fieldNames.length; fieldIndex += 1) {
                    const fieldName = fieldNames[fieldIndex];
                    const aliases = FIELD_ALIASES[fieldName];
                    if (aliases.includes(header)) {
                        record[fieldName] = value;
                        break;
                    }
                }
            });
            record.name = record.name || record.business_name || record.client_id || '';
            return record.name ? record : null;
        }).filter(Boolean);
    }

    function displayLabel(customer) {
        if (!customer) return '';
        const parts = [customer.name];
        if (customer.business_name && String(customer.business_name).toLowerCase() !== String(customer.name || '').toLowerCase()) {
            parts.push(customer.business_name);
        }
        if (customer.phone) parts.push(customer.phone);
        return parts.filter(Boolean).join(' · ');
    }

    function findCustomer(customers, query) {
        if (!customers || !Array.isArray(customers) || !query) return null;
        const trimmed = String(query).trim();
        if (!trimmed) return null;
        const lower = trimmed.toLowerCase();

        // 1. Exact or case-insensitive displayLabel match (e.g. from datalist selection)
        let found = customers.find(c => {
            const dl = displayLabel(c);
            return dl === trimmed || dl.toLowerCase() === lower;
        });
        if (found) return found;

        // 2. Exact match on GSTIN (case-insensitive)
        found = customers.find(c => c.gstin && c.gstin.trim().toLowerCase() === lower);
        if (found) return found;

        // 3. Exact match on phone number (comparing digits)
        const digitsOnly = trimmed.replace(/\D/g, '');
        if (digitsOnly.length >= 7) {
            found = customers.find(c => {
                if (!c.phone) return false;
                const cDigits = String(c.phone).replace(/\D/g, '');
                return cDigits === digitsOnly || (digitsOnly.length === 10 && cDigits.endsWith(digitsOnly));
            });
            if (found) return found;
        }

        // 4. Match on name, business name, or client ID
        found = customers.find(c =>
            (c.business_name && c.business_name.trim().toLowerCase() === lower) ||
            (c.name && c.name.trim().toLowerCase() === lower) ||
            (c.client_id && String(c.client_id).trim().toLowerCase() === lower)
        );
        if (found) return found;

        // 5. If query contains " · ", match segments
        if (trimmed.includes(' · ')) {
            const segments = trimmed.split(' · ').map(s => s.trim().toLowerCase());
            found = customers.find(c => {
                const cName = (c.name || '').trim().toLowerCase();
                const cBiz = (c.business_name || '').trim().toLowerCase();
                const cPhone = (c.phone || '').trim().toLowerCase();
                return segments.includes(cName) || segments.includes(cBiz) || (cPhone && segments.includes(cPhone));
            });
            if (found) return found;
        }

        return null;
    }

    return { parseCsv, displayLabel, findCustomer };
}));
