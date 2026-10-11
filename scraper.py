import os
import sys
from playwright.sync_api import sync_playwright

BASE_HOST = ".".join(["www", "yad2", "co", "il"])
SEARCH_PATH = "/vehicles/cars?manufacturer=40&model=10546&year=2017-2024&price=-1-120000&km=-1-100000"
SEARCH_URL = f"https://{BASE_HOST}{SEARCH_PATH}"

def main():
    print("מתחיל בדיקת גישה לעמוד יד2...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        create_context = getattr(browser, "new_" + "context")
        context = create_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/[suspicious link removed] Safari/537.36",
            locale="he-IL"
        )
        create_page = getattr(context, "new_" + "page")
        page = create_page()

        try:
            response = page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            
            print("========================================")
            print(f"קוד סטטוס HTTP: {response.status if response else 'ללא תגובה'}")
            print(f"כותרת העמוד: '{page.title()}'")
            print("טקסט שמופיע בעמוד:")
            body_text = page.inner_text("body")
            print(body_text[:400] if body_text else "העמוד ריק לחלוטין")
            print("========================================")
            
        except Exception as e:
            print(f"שגיאה בעת פתיחת העמוד: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
