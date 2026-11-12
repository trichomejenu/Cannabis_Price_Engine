import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

TARGET_GROWER = "טריכום"

def scrape_jane_products():
    print(f"Starting advanced stealth scan for grower: {TARGET_GROWER}")
    products_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1920,1080"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="he-IL",
            timezone_id="Asia/Jerusalem"
        )
        
        page = context.new_page()
        
        # הסתרת מאפייני אוטומציה מתוך ה-JavaScript של הדפדפן
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        try:
            print("Navigating to Jane...")
            page.goto("https://jane.co.il/cannabis-products", timeout=60000, wait_until="domcontentloaded")
            
            # המתנה והדמיית גלילה אנושית כדי לעבור את בדיקות האבטחה
            print("Simulating human interaction...")
            page.wait_for_timeout(5000)
            page.mouse.move(200, 200)
            page.mouse.down()
            page.mouse.up()
            page.evaluate("window.scrollBy(0, 500);")
            page.wait_for_timeout(4000)

            # בדיקה האם האתר עדיין חוסם אותנו
            body_text = page.inner_text("body")
            if "גישה נחסמה" in body_text:
                print("Cloudflare block detected. Trying alternative wait...")
                page.wait_for_timeout(10000)
                body_text = page.inner_text("body")

            if "גישה נחסמה" not in body_text:
                print("Access granted! Extracting product items...")
                # ננסה לאסוף אלמנטים של מוצרים או טקסט רלוונטי
                items = page.locator(".product-item, .card, tr, div").all()
                for item in items:
                    try:
                        text = item.inner_text()
                        if TARGET_GROWER in text and len(text) < 500:
                            if text not in [p['details'] for p in products_data]:
                                products_data.append({
                                    "name": text.split('\n')[0],
                                    "details": text
                                })
                    except Exception:
                        continue
                
                # אם לא נמצאו פריטים ממוקדים, ניקח חלקים מהעמוד הראשי
                if not products_data:
                    products_data.append({
                        "name": f"מוצרי {TARGET_GROWER} (כללי)",
                        "details": body_text[:2000]
                    })
            else:
                products_data.append({
                    "name": "שגיאת חסימה",
                    "details": "האתר עדיין חוסם את הגישה האוטומטית בשל הגנת האתר."
                })

        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            browser.close()

    return products_data

def send_email(report_content):
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        return

    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"Price Report - {TARGET_GROWER}"

    html_body = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif;">
        <h2>דו"ח מעקב מחירים - {TARGET_GROWER}</h2>
        <p>תוצאות הסריקה:</p>
        <pre style="background: #f4f4f4; padding: 10px; border-radius: 5px; white-space: pre-wrap;">{report_content}</pre>
        <p>בברכה, <br><b>Jane Price Agent</b></p>
    </div>
    """
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    data = scrape_jane_products()
    if data:
        report = "\n".join([f"• {item['name']}\n  {item['details']}\n" for item in data])
        send_email(report)
