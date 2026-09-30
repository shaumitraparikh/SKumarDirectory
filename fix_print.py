with open("app/templates/print_template.html", "r") as f:
    content = f.read()

# Make sure we initialize it
if "{% set global_sr" not in content:
    content = content.replace("{% for cat in chunk %}", "{% set global_sr = namespace(value=1) %}\n            {% for cat in chunk %}")
    content = content.replace("{{ item.sr_number }}", "{{ global_sr.value }}{% set global_sr.value = global_sr.value + 1 %}")

with open("app/templates/print_template.html", "w") as f:
    f.write(content)
