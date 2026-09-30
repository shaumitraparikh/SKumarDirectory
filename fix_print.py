import re

with open("app/templates/print_template.html", "r") as f:
    content = f.read()

# Replace header block
content = re.sub(r'<div class="header">.*?</div>', '{% include "partials/_header.html" %}', content, flags=re.DOTALL)

# Increase fonts and adjust padding
# body font-size: 8.5pt -> 13pt
content = content.replace("font-size: 8.5pt;", "font-size: 13pt;")
content = content.replace("font-size: 7pt;", "font-size: 11pt;")
content = content.replace("font-size: 7.5pt;", "font-size: 11.5pt;")
content = content.replace("font-size: 8pt;", "font-size: 12pt;")
content = content.replace("font-size: 10pt;", "font-size: 14pt;")

content = content.replace("padding: 2px 3px;", "padding: 1px 2px;")
content = content.replace("padding: 4px 3px;", "padding: 2px 2px;")

with open("app/templates/print_template.html", "w") as f:
    f.write(content)
