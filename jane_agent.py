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
    print(f"Searching API for grower: {TARGET_GROWER}")
    products_data = []

    try:
        # פנייה לכתובת חיפוש או קטלוג פנימית של האתר
        url = "https://jane.co.il/api/products" # או נתיב חיפוש חלופי
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://jane.co.il/cannabis-products"
        }
        
        response = requests.get(url, impersonate="chrome", headers=headers, timeout=30)
        print(f"API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # סינון מוצרים של המגדל
            found = False
            for item in data:
                if TARGET_GROWER in str(item):
                    found = True
                    products_data.append({
                        "name": item.get("name", "מוצר טריכום"),
                        "details": f"מחיר: {item.get('price', 'לא ידוע')} ₪"
                    })
            
            if not found:
                products_data.append({
                    "name": "ה-API תקין אך לא נמצאו פריטים",
                    "data": "התקבלה תשובה מהשרת אך שם המגדל לא אותר במבנה הנתונים."
                })
        else:
            # אם אין גישה ישירה ל-API, נציג הודעה ברורה
            products_data.append({
                "name": "חסימת שרת מלאה",
                "details": "האתר מגן על הנתונים מפני שרתים חיצוניים. מומלץ להריץ את הסקריפט ישירות ממחשב הבית שלך."
            })

    except Exception as e:
        products_data.append({
            "name": "שגיאת תקשורת",
            "details": str(e)
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
        <p>תוצאות:</p>
        <pre style="background: #f4f4f4; padding: 10px; border-radius: 5px; white-space: pre-wrap;">{report_content}</pre>
        <p>בברכה, <br><b>Jane Price Agent</b></p>
    </div>
    """
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    data = scrape_jane_products()
    if data:
        report = "\n".join([f"• {item['name']}\n  {item['details']}\n" for item in data])
        send_email(report)
