with open("app/templates/partials/_header.html", "r") as f:
    content = f.read()

# Make reading friendly
content = content.replace("font-size: 12px;", "font-size: 14px;")
content = content.replace("font-size: 24px;", "font-size: 28px;")
content = content.replace("font-size: 11px;", "font-size: 13px;")
content = content.replace("padding: 6px 12px;", "padding: 10px 15px;")
content = content.replace("margin-bottom: 3px;", "margin-bottom: 6px;")
content = content.replace("margin-bottom: 4px;", "margin-bottom: 8px;")

with open("app/templates/partials/_header.html", "w") as f:
    f.write(content)
