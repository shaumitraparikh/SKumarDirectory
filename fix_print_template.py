import re

with open("app/templates/print_template.html", "r") as f:
    content = f.read()

# Replace the broken part with just the include
content = re.sub(r'\{% include "partials/_header\.html" %\}.*?Effective \{\{ company\.date \}\}</p>\s*</div>', '{% include "partials/_header.html" %}', content, flags=re.DOTALL)

with open("app/templates/print_template.html", "w") as f:
    f.write(content)
