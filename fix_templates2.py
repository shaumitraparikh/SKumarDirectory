import re

for filename in ["app/templates/search_template.html", "app/templates/photo_template.html"]:
    with open(filename, "r") as f:
        content = f.read()
    
    # regex to remove the extra </div> that was left behind
    content = content.replace('{% include "partials/_header.html" %}\n\n</div>', '{% include "partials/_header.html" %}')
    
    with open(filename, "w") as f:
        f.write(content)

