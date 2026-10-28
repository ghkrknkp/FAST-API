"""
Email Alert Dispatcher & Test Utility.
Can be run from the command line or imported by FastAPI to deliver
real email alert notifications to an administrator's inbox.
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from app.config import settings

# Load .env values into environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def send_alert_email(
    to_email: str,
    alert_name: str = "HTTP500Error",
    severity: str = "CRITICAL",
    summary: str = "HTTP 500 Internal Server Error detected on /simulate-error",
    description: str = "Internal server error rate breached configured threshold. Investigated unhandled exception.",
    remediation: str = "Check application logs for traceback. If testing, verify /simulate-error endpoint.",
    smtp_host: str = None,
    smtp_port: int = 587,
    smtp_user: str = None,
    smtp_password: str = None,
) -> dict:
    """
    Sends a formatted HTML and plain-text alert email via SMTP.
    Uses environment variables or passed parameters.
    """
    host = smtp_host or os.getenv("ALERT_EMAIL_SMARTHOST", "smtp.gmail.com")
    # Clean host if port is attached e.g. "smtp.gmail.com:587"
    if ":" in host:
        host_parts = host.split(":")
        host = host_parts[0]
        port = int(host_parts[1])
    else:
        port = smtp_port or int(os.getenv("ALERT_EMAIL_PORT", 587))

    user = smtp_user or os.getenv("ALERT_EMAIL_AUTH_USERNAME")
    password = smtp_password or os.getenv("ALERT_EMAIL_AUTH_PASSWORD")
    sender = os.getenv("ALERT_EMAIL_FROM", user or "alerts@fastapi-monitoring.local")

    if not user or not password:
        return {
            "status": "error",
            "message": "Missing SMTP credentials. Please configure ALERT_EMAIL_AUTH_USERNAME and ALERT_EMAIL_AUTH_PASSWORD in .env",
        }

    # Compose message
    msg = MIMEMultipart("alternative")
    subject = f"[API ALERT - {severity}] {alert_name}: {summary}"
    msg["Subject"] = subject
    msg["From"] = f"FastAPI Monitor <{sender}>"
    msg["To"] = to_email
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # High-contrast, clean HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #09090b; color: #ffffff; padding: 20px; }}
        .card {{ background: #121215; border: 1px solid #27272a; border-radius: 8px; max-width: 600px; margin: 0 auto; overflow: hidden; }}
        .header {{ background: #dc2626; color: #ffffff; padding: 16px 20px; font-size: 18px; font-weight: bold; }}
        .body {{ padding: 24px; }}
        .field {{ margin-bottom: 16px; }}
        .label {{ font-size: 11px; text-transform: uppercase; color: #a1a1aa; font-weight: bold; letter-spacing: 0.5px; }}
        .val {{ font-size: 14px; color: #f4f4f5; margin-top: 4px; line-height: 1.5; }}
        .code {{ font-family: monospace; background: #18181b; padding: 3px 6px; border-radius: 4px; border: 1px solid #27272a; color: #ef4444; }}
        .footer {{ padding: 14px 20px; background: #18181b; border-top: 1px solid #27272a; font-size: 12px; color: #71717a; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">🚨 [ALERT {severity}] {alert_name}</div>
        <div class="body">
          <div class="field">
            <div class="label">Timestamp</div>
            <div class="val">{now_str}</div>
          </div>
          <div class="field">
            <div class="label">Summary</div>
            <div class="val"><strong>{summary}</strong></div>
          </div>
          <div class="field">
            <div class="label">Description</div>
            <div class="val">{description}</div>
          </div>
          <div class="field">
            <div class="label">Recommended SRE Remediation</div>
            <div class="val">{remediation}</div>
          </div>
        </div>
        <div class="footer">
          Delivered by FastAPI API Monitoring & Alertmanager Observability Stack
        </div>
      </div>
    </body>
    </html>
    """

    part_text = MIMEText(f"[{severity}] {alert_name}\n\nSummary: {summary}\nDescription: {description}\nRemediation: {remediation}\nTimestamp: {now_str}", "plain")
    part_html = MIMEText(html_content, "html")
    msg.attach(part_text)
    msg.attach(part_html)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(user, password)
            server.sendmail(sender, to_email, msg.as_string())
        return {
            "status": "success",
            "message": f"Alert email delivered successfully to {to_email}",
            "recipient": to_email,
            "subject": subject,
            "timestamp": now_str,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"SMTP delivery failed: {str(e)}",
        }


if __name__ == "__main__":
    import sys

    recipient = sys.argv[1] if len(sys.argv) > 1 else input("Enter recipient email address: ").strip()
    if not recipient:
        print("Error: No recipient specified.")
        sys.exit(1)

    print(f"Attempting to dispatch test alert email to {recipient}...")
    res = send_alert_email(to_email=recipient)
    print("Result:", res)
