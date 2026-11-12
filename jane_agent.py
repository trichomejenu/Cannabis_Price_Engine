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
    print(f"Starting request scan for grower: {TARGET_GROWER}")
    products_data = []

    try:
        url = "https://jane.co.il/cannabis-products"
        
        # הגדרת כותרות מדויקות שמדמות דפדפן לחלוטין
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://jane.co.il/",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

        # ביצוע הבקשה עם התחזות לדפדפן Chrome ושליחת הכותרות
        response = requests.get(url, impersonate="chrome", headers=headers, timeout=30)
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            html_text = response.text
            
            if "גישה נחסמה" in html_text or "Cloudflare" in html_text or "403" in html_text:
                products_data.append({
                    "name": "שגיאת חסימה",
                    "details": "האתר זיהה את הבקשה כחסומה מאובטחת."
                })
            else:
                # בדיקה האם המגדל מופיע בטקסט של העמוד
                if TARGET_GROWER in html_text:
                    products_data.append({
                        "name": f"מוצרי {TARGET_GROWER} נמצאו בהצלחה!",
                        "details": f"האתר החזיר תשובה תקינה (200) והשם '{TARGET_GROWER}' אותר בתוכן העמוד."
                    })
                else:
                    products_data.append({
                        "name": f"מוצרי {TARGET_GROWER}",
                        "details": "העמוד נטען בהצלחה אך טרם אותר אזכור מדויק בטקסט."
                    })
        else:
            products_data.append({
                "name": "שגיאת שרת",
                "details": f"קוד שגיאה: {response.status_code}"
            })

    except Exception as e:
        print(f"Error: {e}")
        products_data.append({
            "name": "שגיאת מערכת",
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
