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
    print(انט("מתחיל סריקה עבור כל מוצרי המגדל: {TARGET_GROWER}..."))
    products_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # מעבר לעמוד מוצרי הקנאביס באתר
            page.goto("https://jane.co.il/cannabis-products", timeout=60000)
            page.wait_for_timeout(5000) # המתנה לטעינת העמוד והאלמנטים

            # נסיון לאתר את פילטר המגדלים ולסמן את "טריכום" או לחפש ישירות
            # לחלופין, נבצע חיפוש או נגרד את כל המוצרים שמופיעים בטבלה/כרטיסים
            print("🔍 מחפש מוצרים של המגדל ברשת...")
            
            # איסוף כל כרטיסי המוצרים או השורות בטבלה שמופיעים בעמוד
            # נחפש אלמנטים שמכילים את שם המגדל או את רשימת המוצרים
            items = page.locator(".product-item, tr, .card").all()
            
            for item in items:
                text = item.inner_text()
                if TARGET_GROWER in text:
                    # חילוץ נתונים בסיסי מהכרטיס/שורה
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    if lines:
                        product_name = lines[0] # שם המוצר לרוב בשורה הראשונה
                        products_data.append({
                            "name": product_name,
                            "details": text[:200] # תקציר הטקסט והמחירים
                        })

            # אם לא נמצאו פריטים בצורה הזו, ננסה גישה חלופית של חיפוש טקסטואלי
            if not products_data:
                print("⚠️ לא נמצאו פריטים אוטומטית לפי סלקטורים, מנסה לאסוף את כל טקסט העמוד...")
                body_text = page.inner_text("body")
                products_data.append({
                    "name": f"כל מוצרי {TARGET_GROWER}",
                    "details": body_text[:1000]
                })

        except Exception as e:
            print(f"❌ שגיאה במהלך הסריקה: {e}")
        finally:
            browser.close()

    return products_data

def send_email(report_content):
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        print("❌ חסרים נתוני התחברות למייל ב-Environment Variables.")
        return

    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"📊 דו\"ח מחירים מעודכן - מוצרי {TARGET_GROWER}"

    html_body = f"""
    <dir dir="rtl" style="font-family: Arial, sans-serif;">
        <h2>דו"ח מעקב מחירים - {TARGET_GROWER}</h2>
        <p>להלן נתוני המוצרים העדכניים שנסרקו מהאתר:</p>
        <pre style="background: #f4f4f4; padding: 10px; border-radius: 5px;">{report_content}</pre>
        <p>בברכה, <br><b>Jane Price Agent</b></p>
    </dir>
    """
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print("✅ מייל סיכום נשלח בהצלחה!")
    except Exception as e:
        print(f"❌ שגיאה בשליחת המייל: {e}")

if __name__ == "__main__":
    data = scrape_jane_products()
    if data:
        report = "\n".join([f"• {item['name']}\n  {item['details']}\n" for item in data])
        send_email(report)
    else:
        print("⚠️ לא נמצאו מוצרים לשליחה.")
