import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from curl_cffi import requests

EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

TARGET_GROWER = "טריכום"

def scrape_jane_products():
    print(f"Starting API/Direct scan for grower: {TARGET_GROWER}")
    products_data = []

    # ננסה לגשת לנקודת קצה או לעמוד ראשי עם פרופיל דפדפן שונה (Safari / Firefox)
    urls_to_try = [
        "https://jane.co.il/",
        "https://jane.co.il/cannabis-products"
    ]

    success = False
    for url in urls_to_try:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "he-IL,he;q=0.9",
                "Referer": "https://www.google.com/"
            }
            
            # מעבר לאמולציית Safari או Firefox שעוברות טוב יותר הגנות מסוימות
            response = requests.get(url, impersonate="safari15_5", headers=headers, timeout=30)
            print(f"Trying {url} -> Status: {response.status_code}")
            
            if response.status_code == 200:
                html_text = response.text
                if "גישה נחסמה" not in html_text and "403" not in html_text:
                    success = True
                    if TARGET_GROWER in html_text:
                        products_data.append({
                            "name": f"מוצרי {TARGET_GROWER} אותר בהצלחה!",
                            "details": f"הגישה הצליחה דרך {url} ושם המגדל נמצא בתוכן האתר."
                        })
                    else:
                        products_data.append({
                            "name": "האתר זמין אך נדרש מיקוד",
                            "details": f"התקבלה תשובה תקינה מ-{url}, אך שם המגדל לא הופיע בטקסט הגולמי."
                        })
                    break
        except Exception as e:
            print(f"Failed on {url}: {e}")

    if not success:
        products_data.append({
            "name": "שגיאת מעקב",
            "details": "השרת ממשיך לחסום את כתובות ה-IP של GitHub Actions. נדרש מעבר לשיטת פתרון מבוססת פרוקסי או חיפוש ידני."
        })

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
