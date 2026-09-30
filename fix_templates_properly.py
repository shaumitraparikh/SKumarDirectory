import re

for filename in ["app/templates/search_template.html", "app/templates/photo_template.html"]:
    with open(filename, "r") as f:
        content = f.read()
    
    # We want to replace <style>.unified-header ... </style>\n<div class="unified-header"> ... </div>
    # The end of the unified-header block is </div> before <div id="checkoutConfig" hidden
    
    # regex match exactly `<style>\n.unified-header` ... `</div>\n</div>\n`
    # Let's just find `<style>\n.unified-header` and `<div id="checkoutConfig"` (or `<header class="doc-header">` for photo)
    
    start_idx = content.find("<style>\n.unified-header")
    if start_idx == -1:
        start_idx = content.find("<style>\n    .unified-header")
        
    if filename == "app/templates/search_template.html":
        end_idx = content.find("<div id=\"checkoutConfig\"")
    else:
        end_idx = content.find("<!-- Authentic Document Header")
        if end_idx == -1:
            end_idx = content.find("<header class=\"doc-header\">")
            
    if start_idx != -1 and end_idx != -1:
        content = content[:start_idx] + '{% include "partials/_header.html" %}\n\n' + content[end_idx:]
        with open(filename, "w") as f:
            f.write(content)

