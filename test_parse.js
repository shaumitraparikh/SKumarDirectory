const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
const match = html.match(/<script id="catalogData" type="application\/json">([\s\S]*?)<\/script>/);
if (match) {
    const jsonStr = match[1];
    try {
        const data = JSON.parse(jsonStr);
        console.log("Parsed catalog items:", data.length);
    } catch(e) {
        console.log("Parse error:", e);
    }
} else {
    console.log("Not found");
}
