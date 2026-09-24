import time
import sys
from playwright.sync_api import sync_playwright
from src.database.connection import init_db
from src.database.repository import CameraRepository

sys.stdout.reconfigure(encoding='utf-8')
init_db()
cam = CameraRepository.get_camera_by_id(28)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
    context = browser.new_context(http_credentials={"username": cam.username, "password": cam.password})
    page = context.new_page()
    
    # 1. Load setup option first to initialize session & parameters
    print("1. Loading setup option...")
    page.goto(f"http://{cam.ip_or_url}/setup/option.html", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    
    # 2. Now navigate to storage_searching.html
    print("2. Loading storage_searching.html...")
    page.goto(f"http://{cam.ip_or_url}/setup/localstorage/storage_searching.html", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    # 3. Check if {{ target.name }} is compiled now!
    has_target_mustache = page.evaluate("() => document.body.innerText.includes('{{ target.name }}')")
    print(f"Has {{ target.name }}? {has_target_mustache}")
    
    # Fill minutes
    inp = page.locator("input[ng-model='nrecent']").first
    inp.fill("5")
    inp.press("Tab")
    time.sleep(1)
    
    # Click minute(s)
    page.locator("button[btn-radio='60'], button:has-text('minute(s)')").first.click()
    time.sleep(2)
    
    # Check From and To
    from_val = page.locator("#DAUTOID_storage_search_date_begin").input_value()
    to_val = page.locator("#DAUTOID_storage_search_date_end").input_value()
    print(f"From date: '{from_val}', To date: '{to_val}'")
    
    # Click Search
    page.locator("button[ng-click='submit_search()'], button:has-text('Search')").first.click()
    time.sleep(10)
    
    page.screenshot(path="classic_option_first_test.png")
    rows = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('.ngRow, table tbody tr')).map(r => r.innerText.trim()).filter(Boolean);
    }""")
    print("Rows found count:", len(rows))
    for r in rows:
        print("Row:", r)

    browser.close()
