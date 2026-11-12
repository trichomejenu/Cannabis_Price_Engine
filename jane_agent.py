import asyncio
from datetime import datetime
import json
import os
import re
import smtplib
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

TARGET_PRODUCT = "קארבו"
TARGET_BRAND = "טריכום"
SEARCH_URL = f"https://jane.co.il/products/?q={TARGET_PRODUCT}"
HISTORY_FILE = "price_history.json"


def load_history():
  if os.path.exists(HISTORY_FILE):
    try:
      with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception as e:
      print(f"⚠️ שגיאה בטעינת קובץ ההיסטוריה: {e}")
  return {}


def save_and_push_history(data):
  try:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
    print(
        f"💾 קובץ {HISTORY_FILE} נשמר מקומית בהצלחה. מעדכן ב-GitHub..."
    )

    # ביצוע פעולות Git ישירות מתוך הסקריפט
    subprocess.run(
        ["git", "config", "--global", "user.name", "Price Bot"], check=False
    )
    subprocess.run(
        [
            "git",
            "config",
            "--global",
            "user.email",
            "bot@users.noreply.github.com",
        ],
        check=False,
    )
    subprocess.run(["git", "add", HISTORY_FILE], check=False)
    subprocess.run(
        ["git", "commit", "-m", "Auto-update price history via script"],
        capture_output=True,
        text=True,
    )
    push_res = subprocess.run(
        ["git", "push", "origin", "HEAD:main"], capture_output=True, text=True
    )
    print("📤 תוצאת עדכון ה-Git:", push_res.stdout, push_res.stderr)

  except Exception as e:
    print(f"❌ שגיאה בשמירה/דחיפה של קובץ ההיסטוריה: {e}")


def send_email_alert(drops):
  if not drops:
    return

  msg = MIMEMultipart()
  msg["From"] = EMAIL_SENDER
  msg["To"] = EMAIL_RECEIVER
  msg["Subject"] = (
      f"🚨 תזוזת מחיר ראשונה ביום ל-{TARGET_PRODUCT} ({TARGET_BRAND})"
  )

  html_rows = ""
  for item in drops:
    html_rows += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{item['product']}</td>
            <td style="padding: 8px; border: 1px solid #ddd;"><b>{item['pharmacy']}</b></td>
            <td style="padding: 8px; border: 1px solid #ddd; color: green;"><b>₪{item['new_price']}</b></td>
            <td style="padding: 8px; border: 1px solid #ddd; text-decoration: line-through;">₪{item['old_price']}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">-₪{item['diff']}</td>
            <td style="padding: 8px; border: 1px solid #ddd; color: #555;">{item['time']}</td>
        </tr>
        """

  body = f"""
    <html dir="rtl">
    <body style="font-family: Arial, sans-serif; direction: rtl; text-align: right;">
        <h2>זוהתה ירידת מחיר (ראשונה להיום) עבור {TARGET_PRODUCT} ({TARGET_BRAND})!</h2>
        <table style="border-collapse: collapse; width: 100%; max-width: 700px;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th style="padding: 8px; border: 1px solid #ddd;">מוצר</th>
                    <th style="padding: 8px; border: 1px solid #ddd;">ספק (בית מרקחת)</th>
                    <th style="padding: 8px; border: 1px solid #ddd;">מחיר חדש</th>
                    <th style="padding: 8px; border: 1px solid #ddd;">מחיר קודם</th>
                    <th style="padding: 8px; border: 1px solid #ddd;">חיסכון</th>
                    <th style="padding: 8px; border: 1px solid #ddd;">שעת השינוי</th>
                </tr>
            </thead>
            <tbody>
                {html_rows}
            </tbody>
        </table>
        <p><a href="{SEARCH_URL}">למעבר לעמוד המוצר באתר Jane</a></p>
    </body>
    </html>
    """

  msg.attach(MIMEText(body, "html", "utf-8"))

  try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
      server.login(EMAIL_SENDER, EMAIL_PASSWORD)
      server.send_message(msg)
    print("✅ התראת מייל נשלחה בהצלחה!")
  except Exception as e:
    print(f"❌ שגיאה בשליחת המייל: {e}")


async def scrape_jane():
  now = datetime.now()
  current_date_str = now.strftime("%Y-%m-%d")
  current_time_str = now.strftime("%H:%M:%S")

  print(
      f"🔍 מתחיל סריקה עבור: {TARGET_PRODUCT} של {TARGET_BRAND} ב-"
      f" {current_date_str} בשעה {current_time_str}..."
  )

  history = load_history()
  price_drops = []

  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = await context.new_page()

    try:
      await page.goto(
          SEARCH_URL, wait_until="domcontentloaded", timeout=30000
      )
      await page.wait_for_timeout(3000)

      product_links = await page.locator("a").all()
      target_href = None

      for link in product_links:
        try:
          text = await link.inner_text()
          if TARGET_PRODUCT in text and TARGET_BRAND in text:
            target_href = await link.get_attribute("href")
            break
        except:
          continue

      if not target_href:
        print("⚠️ לא נמצא עמוד מוצר תואם בחיפוש.")
        await browser.close()
        return

      full_product_url = (
          f"https://jane.co.il{target_href}"
          if target_href.startswith("/")
          else target_href
      )
      print(f"📄 נכנס לעמוד המוצר: {full_product_url}")

      await page.goto(
          full_product_url, wait_until="domcontentloaded", timeout=30000
      )
      await page.wait_for_timeout(3000)

      rows = await page.locator("div, tr, li").all()
      current_offers = {}

      for row in rows:
        try:
          text = await row.inner_text()
          if "₪" in text and 10 < len(text) < 150:
            price_match = re.search(
                r"(\d+(?:\.\d+)?)\s*₪|₪\s*(\d+(?:\.\d+)?)", text
            )
            if price_match:
              price_val = float(price_match.group(1) or price_match.group(2))
              lines = [
                  line.strip()
                  for line in text.split("\n")
                  if line.strip() and "₪" not in line
              ]
              if lines:
                pharmacy_name = lines[0]
                if (
                    pharmacy_name not in current_offers
                    or price_val < current_offers[pharmacy_name]
                ):
                  current_offers[pharmacy_name] = price_val
        except:
          continue

    except Exception as e:
      print(f"❌ שגיאה במהלך הסריקה: {e}")
      await browser.close()
      return

    await browser.close()

  if not current_offers:
    print("⚠️ לא זוהו הצעות מחיר פעילות בעמוד המוצר.")
    return

  if "products_history" not in history:
    history["products_history"] = {}

  prod_key = f"{TARGET_PRODUCT}_{TARGET_BRAND}"
  if prod_key not in history["products_history"]:
    history["products_history"][prod_key] = {}

  product_records = history["products_history"][prod_key]

  for pharmacy, current_price in current_offers.items():
    print(f"   - {pharmacy}: ₪{current_price}")
    last_known_price = product_records.get(pharmacy, {}).get("price")

    if last_known_price is not None and current_price < last_known_price:
      last_alert_date = product_records.get(pharmacy, {}).get(
          "last_alert_date"
      )

      if last_alert_date != current_date_str:
        price_drops.append({
            "product": f"{TARGET_PRODUCT} ({TARGET_BRAND})",
            "pharmacy": pharmacy,
            "new_price": current_price,
            "old_price": last_known_price,
            "diff": round(last_known_price - current_price, 2),
            "time": f"{current_date_str} בשעה {current_time_str}",
        })
        product_records[pharmacy]["last_alert_date"] = current_date_str

    if pharmacy not in product_records:
      product_records[pharmacy] = {}
    product_records[pharmacy]["price"] = current_price
    product_records[pharmacy]["last_checked"] = (
        f"{current_date_str} {current_time_str}"
    )

  # שמירה ודחיפה אוטומטית לענן מתוך הפייתון
  save_and_push_history(history)

  if price_drops:
    send_email_alert(price_drops)
  else:
    print("ℹ️ הסריקה הסתיימה והנתונים עודכנו ב-GitHub.")


if __name__ == "__main__":
  asyncio.run(scrape_jane())
