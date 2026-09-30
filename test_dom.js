const fs = require('fs');
const jsdom = require("jsdom");
const { JSDOM } = jsdom;

const html = fs.readFileSync('index.html', 'utf8');
const js1 = fs.readFileSync('app/assets/js/commerce_core.js', 'utf8');
const js2 = fs.readFileSync('app/assets/js/bill_archive.js', 'utf8');
const js3 = fs.readFileSync('app/assets/js/search_catalog.js', 'utf8');

const dom = new JSDOM(html, { runScripts: "dangerously" });
dom.window.eval(js1);
dom.window.eval(js2);
try {
  dom.window.eval(js3);
} catch (e) {
  console.log("ERROR IN JS:", e);
}
console.log("Items in grid:", dom.window.document.getElementById('catalogGrid').children.length);
