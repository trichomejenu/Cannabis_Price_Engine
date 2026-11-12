import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

# הגדרות שליחה מתוך ה-Secrets של GitHub
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

TARGET_GROWER = "טריכום"

def scrape_jane_products():
    print(f"Starting scan for grower: {TARGET_GROWER}")
    products_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # מעבר לעמוד מוצרי הקנאביס באתר
            page.goto("https://jane.co.il/cannabis-products", timeout=60000)
            page.wait_for_timeout(5000) # המתנה לטעינת העמוד

            print("Searching for items on page...")
            
            # איסוף אלמנטים מהעמוד
            items = page.locator(".product-item, tr, .card").all()
            
            for item in items:
                try:
                    text = item.inner_text()
                    if TARGET_GROWER in text:
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        if lines:
                            product_name = lines[0]
                            products_data.append({
                                "name": product_name,
                                "details": text[:200]
                            })
                except Exception:
                    continue

            # אם לא נמצאו פריטים באופן ספציפי, ניקח את תוכן העמוד הכללי
            if not products_data:
                print("Fallback: collecting general page text...")
                body_text = page.inner_text("body")
                products_data.append({
                    "name": f"All products for {TARGET_GROWER}",
                    "details": body_text[:1000]
                })

        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            browser.close()

    return products_data

def send_email(report_content):
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        print("Missing email configuration variables.")
        return

    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"Price Report - {TARGET_GROWER}"

    html_body = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif;">
        <h2>דו"ח מעקב מחירים - {TARGET_GROWER}</h2>
        <p>להלן נתוני המוצרים העדכניים שנסרקו מהאתר:</p>
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
    else:
        print("No products found to send.")
