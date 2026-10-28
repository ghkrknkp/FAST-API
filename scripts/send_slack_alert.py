"""
Slack Alert Notification Dispatcher.
Tests incoming webhooks and delivers formatted incident alert cards to Slack channels.
"""

import os
import requests
from datetime import datetime, timezone

# Load .env values into environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def send_slack_alert(
    webhook_url: str = None,
    channel: str = "#api-alerts",
    alert_name: str = "HTTP500Error",
    severity: str = "CRITICAL",
    summary: str = "HTTP 500 Internal Server Error detected on /simulate-error",
    remediation: str = "Check application logs for traceback. If testing, verify /simulate-error endpoint.",
) -> dict:
    """
    Posts a rich Block Kit formatted incident message to a Slack incoming webhook.
    """
    url = webhook_url or os.getenv("ALERT_SLACK_WEBHOOK_URL")

    if not url or "hooks.slack.com" not in url:
        return {
            "status": "error",
            "message": "Missing or invalid ALERT_SLACK_WEBHOOK_URL. Please provide a valid Slack webhook URL.",
        }

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    color = "#ef4444" if severity.upper() == "CRITICAL" else "#f59e0b"

    payload = {
        "channel": channel,
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🚨 [{severity.upper()}] {alert_name}",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Severity:*\n`{severity.upper()}`"},
                            {"type": "mrkdwn", "text": f"*Time:*\n{now_str}"},
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Summary:*\n{summary}\n\n*Recommended Remediation:*\n{remediation}",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "Delivered by FastAPI API Monitoring & Prometheus Alertmanager",
                            }
                        ],
                    },
                ],
            }
        ],
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return {"status": "success", "message": "Alert notification delivered to Slack successfully!"}
        else:
            return {"status": "error", "message": f"Slack API error (HTTP {r.status_code}): {r.text}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to send Slack alert: {str(e)}"}


if __name__ == "__main__":
    import sys

    webhook = sys.argv[1] if len(sys.argv) > 1 else input("Enter your Slack Webhook URL: ").strip()
    res = send_slack_alert(webhook_url=webhook)
    print("Result:", res)
