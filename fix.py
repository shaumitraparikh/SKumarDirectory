with open('app/templates/search_template.html', 'r') as f:
    code = f.read()

# Fix 1: Sticky wrapper
old1 = '<div class="super-sticky-wrapper" style="position: sticky; top: 0; display: flex;'
new1 = '<div class="super-sticky-wrapper" style="position: sticky; top: 0; z-index: 1000; display: flex;'
code = code.replace(old1, new1)

# Fix 2: Cache buster
old2 = '<link rel="stylesheet" href="app/assets/css/search_catalog.css" />'
new2 = '<link rel="stylesheet" href="app/assets/css/search_catalog.css?v={{ catalog_version }}" />'
code = code.replace(old2, new2)

# Fix 3: Tax rows hidden
old3 = '".tax-settings-card," +'
new3 = '".tax-settings-card," +\n              "/* Hide tax rows and clear cart from public */\n              \\\".tax-row, #clearCartButton { display: none !important; }" +'
code = code.replace(old3, new3)

with open('app/templates/search_template.html', 'w') as f:
    f.write(code)
