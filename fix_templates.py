import re

for filename in ["app/templates/search_template.html", "app/templates/photo_template.html"]:
    with open(filename, "r") as f:
        content = f.read()
    
    # regex to match from <style>.*.unified-header.* to the end of the unified-header div
    # In search and photo, it's followed by <div id="checkoutConfig" or <div class="photo-controls"
    content = re.sub(r'<style>\s*\.unified-header.*?</div>\s*</div>\s*', '{% include "partials/_header.html" %}\n\n', content, flags=re.DOTALL)
    
    with open(filename, "w") as f:
        f.write(content)

with open("app/templates/print_template.html", "r") as f:
    content = f.read()
    content = re.sub(r'<div class="print-header">.*?</div>\s*</div>\s*</div>', '{% include "partials/_header.html" %}', content, flags=re.DOTALL)
    with open("app/templates/print_template.html", "w") as f:
        f.write(content)

