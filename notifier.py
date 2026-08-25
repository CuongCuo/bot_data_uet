import sys
import os
import requests
import html
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Telegram configurations
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# SMTP configurations
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
try:
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
except (TypeError, ValueError):
    SMTP_PORT = 587
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

def send_telegram_message(text: str) -> bool:
    """Sends an HTML formatted message via Telegram Bot API."""
    if not BOT_TOKEN or not CHAT_ID:
        # Silently skip if Telegram is not configured, console logging is handled in fallback
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[LỖI] Gửi tin Telegram thất bại: {e}")
        return False

def notify_new_items(items: list[dict]):
    """Sends individual Telegram messages for each new item."""
    for item in items:
        source_name = html.escape(item.get("source_name", "Nguồn tin"))
        title = html.escape(item.get("title", "Không có tiêu đề"))
        link = item.get("link", "")
        item_type = item.get("type", "news")
        
        emoji = "🎓"
        if item_type == "company":
            emoji = "💼"
        elif item_type == "club":
            emoji = "🤝"
        elif item_type == "facebook":
            emoji = "📱"
            
        msg = f"{emoji} <b>{source_name}</b>\n\n{title}\n\n🔗 Link: {link}"
        send_telegram_message(msg)

def generate_email_html(items: list[dict]) -> str:
    """Generates a styled HTML email digest containing all new items."""
    items_html = ""
    
    for item in items:
        source_name = html.escape(item.get("source_name", "Nguồn tin"))
        title = html.escape(item.get("title", "Không có tiêu đề"))
        link = item.get("link", "")
        item_type = item.get("type", "news")
        
        badge_color = "#3b82f6"  # Blue for school
        if item_type == "faculty":
            badge_color = "#10b981"  # Emerald green
        elif item_type == "company":
            badge_color = "#f59e0b"  # Amber
        elif item_type == "facebook":
            badge_color = "#1877f2"  # Facebook blue
            
        items_html += f"""
        <div class="item">
          <span class="badge" style="background-color: {badge_color};">{source_name}</span>
          <div class="item-title">{title}</div>
          <a class="item-link" href="{link}" target="_blank">Xem chi tiết bài viết</a>
        </div>
        """
        
    html_body = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 20px; }}
          .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1); overflow: hidden; border: 1px solid #e2e8f0; }}
          .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 30px 20px; text-align: center; }}
          .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
          .header p {{ margin: 8px 0 0 0; font-size: 14px; color: #94a3b8; }}
          .content {{ padding: 20px 25px; }}
          .item {{ padding: 20px 0; border-bottom: 1px solid #f1f5f9; }}
          .item:last-child {{ border-bottom: none; }}
          .badge {{ display: inline-block; padding: 4px 8px; font-size: 11px; font-weight: 700; color: #ffffff; border-radius: 4px; text-transform: uppercase; margin-bottom: 8px; }}
          .item-title {{ font-size: 16px; font-weight: 600; color: #0f172a; margin: 5px 0 10px 0; line-height: 1.4; }}
          .item-link {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: 600; transition: background-color 0.2s; }}
          .footer {{ background-color: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #f1f5f9; }}
          .footer a {{ color: #2563eb; text-decoration: none; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>🎓 Bản Tin Học Bổng & Việc Làm UET/FET</h1>
            <p>Tổng hợp tin mới nhất trong ngày</p>
          </div>
          <div class="content">
            {items_html}
          </div>
          <div class="footer">
            <p>Hệ thống crawl tin tức tự động trường Đại học Công nghệ & Khoa ĐTVT.</p>
            <p>Github Workflow execution. Không trả lời lại email này.</p>
          </div>
        </div>
      </body>
    </html>
    """
    return html_body

def send_email_digest(items: list[dict]) -> bool:
    """Compiles new items and sends a single consolidated HTML email digest via SMTP."""
    if not items:
        return False
        
    html_content = generate_email_html(items)
    
    if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
        print("\n[WARNING] SMTP credentials not fully configured (SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL).")
        print("Fallback: Printing generated HTML email digest to console:")
        print("=" * 60)
        print(html_content)
        print("=" * 60)
        return False

    # Create MIME message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🎓 [{len(items)} Tin Mới] Bản Tin Học Bổng & Việc Làm UET/FET"
    msg['From'] = f"UET Scholarship Bot <{SENDER_EMAIL}>"
    msg['To'] = RECIPIENT_EMAIL
    
    # Attach HTML content
    part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(part)
    
    try:
        print(f"Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        print("Logging in to SMTP server...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        print(f"Sending email from {SENDER_EMAIL} to {RECIPIENT_EMAIL}...")
        server.sendmail(SENDER_EMAIL, [RECIPIENT_EMAIL], msg.as_string())
        server.quit()
        print("Email digest sent successfully!")
        return True
    except Exception as e:
        print(f"[LỖI] Gửi email thất bại: {e}")
        # Print fallback to console
        print("\n[FALLBACK CONSOLE OUTPUT (HTML Digest)]:")
        print("=" * 60)
        print(html_content)
        print("=" * 60)
        return False
