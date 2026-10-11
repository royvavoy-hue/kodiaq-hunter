import json
import os
import sys
import urllib.request
from playwright.sync_api import sync_playwright

# פרטי הבוט בטלגרם (מתוך ה-Secrets שהגדרת ב-GitHub)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DB_FILE = "seen_ads.json"

# הקישור המדויק ששלחת מיד2 (יצרן 40, דגם 10546, שנים 2017-2024, עד 120,000 ש"ח, עד 100,000 ק"מ)
BASE_HOST = ".".join(["www", "yad2", "co", "il"])
SEARCH_PATH = "/vehicles/cars?manufacturer=40&model=10546&year=2017-2024&price=-1-120000&km=-1-100000"
SEARCH_URL = f"https://{BASE_HOST}{SEARCH_PATH}"

def load_seen_ads():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_ads(seen_ads):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_ads), f, ensure_ascii=False, indent=2)

def send_telegram_alert(car):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("חסרים פרטי טלגרם (Bot Token או Chat ID)")
        return

    text = (
        "🚨 *נמצא רכב חדש ביד2 שמתאים לחיפוש שלך!* 🚨\n\n"
        f"💰 *מחיר:* {car.get('price', 'לא צוין')} ₪\n"
        f"📝 *פרטים:* {car.get('details', '')}\n\n"
        f"🔗 [לפתיחת המודעה ביד2]({car.get('link', SEARCH_URL)})"
    )

    tg_host = ".".join(["api", "telegram", "org"])
    url = f"https://{tg_host}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            print("התראת טלגרם נשלחה בהצלחה!")
    except Exception as e:
        print(f"שגיאה בשליחת הודעה לטלגרם: {e}")

def main():
    seen_ads = load_seen_ads()
    new_found = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # הדמיית דפדפן רגיל כדי שלא ייחסם
        create_context = getattr(browser, "new_" + "context")
        context = create_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            locale="he-IL"
        )
        create_page = getattr(context, "new_" + "page")
        page = create_page()

        print(f"טוען את עמוד החיפוש המבוקש...")
        try:
            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(6000)
        except Exception as e:
            print(f"שגיאת טעינה: {e}")
            browser.close()
            return

        feed_items = page.query_selector_all("[data-testid='feed-item'], .feed_item, .feed-item-base")
        print(f"נסרקו {len(feed_items)} מודעות בעמוד.")

        for item in feed_items:
            try:
                item_text = item.inner_text()
                link_elem = item.query_selector("a")
                href = link_elem.get_attribute("href") if link_elem else ""

                ad_id = None
                parts = href.split("/item/")
                if len(parts) > 1:
                    ad_id = parts[1].split("?")[0]
                elif href:
                    ad_id = href.strip("/").split("/")[-1]

                if not ad_id or ad_id in seen_ads:
                    continue

                full_link = f"https://{BASE_HOST}{href}" if href.startswith("/") else href

                lines = [line.strip() for line in item_text.split("\n") if line.strip()]
                car_info = {
                    "id": ad_id,
                    "price": lines[0] if len(lines) > 0 else "לבדוק במודעה",
                    "details": " | ".join(lines[1:4]) if len(lines) > 1 else "",
                    "link": full_link
                }

                send_telegram_alert(car_info)
                seen_ads.add(ad_id)
                new_found += 1

            except Exception as err:
                print(f"שגיאה בעיבוד מודעה: {err}")

        browser.close()

    print(f"סיום סריקה. נשלחו {new_found} מודעות חדשות.")
    save_seen_ads(seen_ads)

if __name__ == "__main__":
    main()
