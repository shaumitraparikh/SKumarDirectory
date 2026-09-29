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
        return [customer.name, customer.business_name, customer.phone]
            .filter(Boolean).join(' · ');
    }

    function findCustomer(customers, label) {
        return customers.find(customer => displayLabel(customer) === label) || null;
    }

    return { parseCsv, displayLabel, findCustomer };
}));
