const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto('file:///Users/vikenparikh/Downloads/SKumarDirectory/index.html');
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: 'scratch/screenshot.png' });
  await browser.close();
})();
