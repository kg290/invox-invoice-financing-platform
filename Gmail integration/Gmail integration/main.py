"""
Gmail Automation - Main Script
Send automated email notifications using Gmail API
"""

from gmail_service import GmailService, quick_send
from config import EMAIL_CONFIG


def send_hello_world():
    """Send a simple Hello World test email"""
    gmail = GmailService()
    gmail.authenticate()
    
    # Send test email
    result = gmail.send_email(
        to=EMAIL_CONFIG['default_recipient'],
        subject="Hello World - Gmail Automation Test",
        body="Hello World!\n\nThis is a test email from your Gmail Automation System.\n\nYour email integration is working successfully! 🎉"
    )
    
    if result:
        print("✅ Hello World email sent successfully!")
    else:
        print("❌ Failed to send email")
    
    return result


def send_notification(recipient, title, message):
    """
    Send a notification email
    
    Args:
        recipient: Email address to send notification to
        title: Notification title
        message: Notification message content
    """
    gmail = GmailService()
    gmail.authenticate()
    
    subject = f"[Notification] {title}"
    body = f"""
Notification Alert
==================

{title}

{message}

---
This is an automated notification from your Gmail Automation System.
    """
    
    return gmail.send_email(to=recipient, subject=subject, body=body)


def send_html_notification(recipient, title, message):
    """
    Send a styled HTML notification email
    
    Args:
        recipient: Email address to send notification to
        title: Notification title
        message: Notification message content
    """
    gmail = GmailService()
    gmail.authenticate()
    
    subject = f"[Notification] {title}"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .container {{
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #4285f4;
                color: white;
                padding: 20px;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                background-color: #f8f9fa;
                padding: 20px;
                border: 1px solid #e0e0e0;
                border-radius: 0 0 8px 8px;
            }}
            .footer {{
                margin-top: 20px;
                font-size: 12px;
                color: #666;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🔔 {title}</h2>
            </div>
            <div class="content">
                <p>{message}</p>
            </div>
            <div class="footer">
                <p>This is an automated notification from your Gmail Automation System.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return gmail.send_email(to=recipient, subject=subject, body=html_body, html=True)


def main():
    """Main function - demonstrates email sending capabilities"""
    print("=" * 50)
    print("Gmail Automation System")
    print("=" * 50)
    print()
    
    # Check if config is set up
    if EMAIL_CONFIG['default_recipient'] == 'your-email@example.com':
        print("⚠️  Please update config.py with your email address first!")
        print("   Edit EMAIL_CONFIG['default_recipient'] with your email.")
        return
    
    print("Sending Hello World test email...")
    send_hello_world()


if __name__ == "__main__":
    main()
