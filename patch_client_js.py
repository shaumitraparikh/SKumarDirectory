import re

with open('assets/js/search_catalog.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Update fetch to try local API first, then fallback to relative URL
auto_load_logic = '''
// Auto-load server client data if available
fetch('http://127.0.0.1:8766/api/clients')
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => {
        // Convert JSON back to CSV string format for the existing parser, or just bypass it
        // Actually, window.ClientDirectory.loadCsv expects text.
        // Let's just fallback to fetching the CSV directly if the local API isn't running
        throw new Error('Fallback to CSV');
    })
    .catch(() => {
        return fetch('data/client_data.csv')
            .then(response => {
                if (response.ok) return response.text();
                throw new Error('No server client data found.');
            })
            .then(text => {
                const count = window.ClientDirectory.loadCsv(text);
                document.getElementById('clientDirectoryStatus').textContent = 'Loaded ' + count + ' customers from database.';
                var btn = document.getElementById('loadClientsButton');
                if (btn) btn.style.display = 'none';
            });
    })
    .catch(() => { /* Silent failure */ });
'''

js = re.sub(r"fetch\('data/client_data\.csv'\).*?\.catch\(\(\) => \{ /\* Silent failure, fallback to manual upload \*/ \}\);", auto_load_logic.strip(), js, flags=re.DOTALL)

# Add logic to POST to /api/clients/add when generateBill or WhatsApp is clicked
# I'll hook into getBuyerDetails() which is called by both!
buyer_logic = '''function getBuyerDetails() {
    const details = {
        name: document.getElementById('buyerName').value.trim(),
        phone: document.getElementById('buyerPhone').value.trim(),
        email: document.getElementById('buyerEmail').value.trim(),
        address: document.getElementById('buyerAddress').value.trim(),
        state: document.getElementById('buyerState').value.trim(),
        pincode: document.getElementById('buyerPincode').value.trim(),
        gstin: document.getElementById('buyerGstin').value.trim(),
        date: new Date().toLocaleDateString('en-IN')
    };
    
    // Auto-save this customer if local seller is running
    if (details.name && isLocal) {
        fetch('http://127.0.0.1:8766/api/clients/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(details)
        }).catch(() => {});
    }
    
    return details;
}'''

js = re.sub(r"function getBuyerDetails\(\) \{.*?return details;\n\}", buyer_logic.strip(), js, flags=re.DOTALL)

with open('assets/js/search_catalog.js', 'w', encoding='utf-8') as f:
    f.write(js)
