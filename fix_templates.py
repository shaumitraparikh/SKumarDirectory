import re

# 1. FIX SEARCH TEMPLATE
with open('app/templates/search_template.html', 'r', encoding='utf-8') as f:
    search_html = f.read()

# Replace Header
old_header = r'<div class=\"unified-header\" style=\"text-align: center; border-bottom: 2px solid #102a43;.*?Scope:.*?</div>\s*</div>'
new_header = '''<style>
.unified-header { text-align: center; border-bottom: 2px solid #102a43; padding: 12px 15px; margin-bottom: 15px; background: #fff; font-family: 'Segoe UI', system-ui, sans-serif; }
.biz-group { line-height: 1.15; margin-bottom: 8px; }
.biz-sub { font-size: 13px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 2px 0; }
.biz-main { font-size: 28px; font-weight: 800; color: #0f172a; margin: 0; letter-spacing: 0.5px; }
.contact-group { font-size: 12px; color: #334155; line-height: 1.4; max-width: 850px; margin: 0 auto; }
.contact-row { margin-bottom: 3px; }
.contact-row strong { color: #1e293b; font-weight: 600; }
.contact-row a { color: inherit; text-decoration: none; border-bottom: 1px dotted #94a3b8; transition: all 0.2s; }
.contact-row a:hover { color: #2563eb; border-bottom-style: solid; }
.c-pipe { margin: 0 6px; color: #cbd5e1; }
.scope-row { margin-top: 6px; font-size: 11.5px; color: #475569; font-style: italic; }
@media (max-width: 650px) {
    .biz-main { font-size: 24px; }
    .contact-row { display: flex; flex-direction: column; padding-bottom: 4px; border-bottom: 1px solid #f1f5f9; margin-bottom: 4px; }
    .contact-row:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
    .c-pipe { display: none; }
}
</style>
<div class="unified-header">
    <div class="biz-group">
        <div class="biz-sub">General Supply Corporation</div>
        <h1 class="biz-main">S. Kumar &amp; Bros.</h1>
    </div>
    <div class="contact-group">
        <div class="contact-row">
            <strong>Shaumitra G. Parikh</strong> <span class="c-pipe">|</span> Mobile: <a href="tel:+919821361314">9821361314</a>, <a href="tel:+918369398586">8369398586</a> &middot; <a href="tel:35989674">35989674</a> <span class="c-pipe">|</span> GSTIN: 27AAGPP1621C1Z5
        </div>
        <div class="contact-row">
            <strong>Amit G. Parikh</strong> <span class="c-pipe">|</span> Mobile: <a href="tel:+919869905779">9869905779</a> &middot; <a href="tel:45242910">45242910</a> <span class="c-pipe">|</span> GSTIN: 27ACJPP2955J1Z4
        </div>
        <div class="contact-row" style="margin-top: 5px;">
            <a href="https://maps.app.goo.gl/LwzbK7p13RpRza3u8" target="_blank" rel="noopener">3rd Central Building, Grd. Flr., 11, Bomanji Master Road, Mumbai - 400 002.</a>
        </div>
        <div class="scope-row">
            <strong>Scope:</strong> Empire, Fibreglass, Cotton, Silicon, Teflon, PVC, Tube, Cable, Wire, Cloth, Tape &middot; Solder Items, Tester, Fuse Wire.
        </div>
    </div>
</div>'''
search_html = re.sub(old_header, new_header, search_html, flags=re.DOTALL)

# Remove seller css
search_html = re.sub(r'<link rel="stylesheet" href="tools/seller/seller_editor\.css" id="sellerCss" disabled>\n?', '', search_html)

# Remove seller script block and tools section and dialog
search_html = re.sub(r'<script>\s*// Check if we are running locally.*?<dialog class="seller-editor-dialog" style="display: none;" id="sellerEditorDialog" aria-labelledby="sellerEditorTitle">.*?</dialog>', '', search_html, flags=re.DOTALL)

# Remove mode toggle buttons
search_html = re.sub(r'<a href="\?edit=false" class="mode-toggle-btn mode-toggle-customer".*?</script>', '', search_html, flags=re.DOTALL)

# Remove seller js script injection
search_html = re.sub(r'if \(isEditMode\) \{.*?document\.body\.appendChild\(script\);\s*// Hide cart button.*?\}\s*', '', search_html, flags=re.DOTALL)

with open('app/templates/search_template.html', 'w', encoding='utf-8') as f:
    f.write(search_html)


# 2. FIX PHOTO TEMPLATE
with open('app/templates/photo_template.html', 'r', encoding='utf-8') as f:
    photo_html = f.read()
photo_html = re.sub(old_header, new_header, photo_html, flags=re.DOTALL)

with open('app/templates/photo_template.html', 'w', encoding='utf-8') as f:
    f.write(photo_html)

print("Fixed search and photo templates.")
