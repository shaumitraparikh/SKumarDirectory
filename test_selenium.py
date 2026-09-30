import sys
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

try:
    driver = webdriver.Chrome(options=chrome_options)
    url = "file://" + os.path.abspath("index.html")
    driver.get(url)
    logs = driver.get_log('browser')
    for log in logs:
        print(f"[{log['level']}] {log['message']}")
    driver.quit()
except Exception as e:
    print("Selenium error:", e)
