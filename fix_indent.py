import re
with open('tools/seller/local_seller.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Just re-indent everything inside do_POST
text = text.replace('            if self.path == "/api/clients":', '            if self.path == "/api/clients":') # was 12
text = text.replace('                self.send_json(200, {"clients": read_clients()})', '                self.send_json(200, {"clients": read_clients()})') # was 16

# I'll just rewrite the whole file nicely using ast/astor or just redownload the previous commit and apply it right.
