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
        # ביצוע בקשה עם התחזות מלאה לדפדפן Chrome דרך הרשת
        response = requests.get(url, impersonate="chrome", timeout=30)
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            html_text = response.text
            
            if "גישה נחסמה" in html_text or "Cloudflare" in html_text:
                print("Blocked by security wall.")
                products_data.append({
                    "name": "שגיאת חסימה",
                    "details": "האתר חוסם את הבקשה האוטומטית."
                })
            else:
                print("Access successful! Processing page content...")
                products_data.append({
                    "name": f"מוצרי {TARGET_GROWER}",
                    "details": "העמוד התקבל בהצלחה. האתר מאפשר כעת גישה לנתונים."
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
