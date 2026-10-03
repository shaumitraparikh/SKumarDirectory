with open('app/assets/js/search_catalog.js', 'r') as f:
    code = f.read()

import re

old = """            return fetch("/api/bills/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(order)
            }).then(r => r.json()).then(res => {
                if (res.success) {"""

new = """            return fetch("/api/bills/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(order)
            }).then(r => r.json()).then(res => {
                if (res.success) {
                    if (res.added && res.added.id && res.added.id !== reference) {
                        document.getElementById("pInvNo").innerText = res.added.id;
                        order.id = res.added.id;
                        order.html = standaloneBillHtml();
                        fetch("/api/bills/add", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify(order)
                        }).catch(e => console.warn(e));
                    }"""

code = code.replace(old, new)
with open('app/assets/js/search_catalog.js', 'w') as f:
    f.write(code)
