# Gmail Automation System

A Python-based Gmail integration for sending automated email notifications.

## Features

- ✅ Send plain text emails
- ✅ Send HTML formatted emails
- ✅ Send emails with attachments
- ✅ OAuth 2.0 authentication (secure)
- ✅ Easy-to-use API

## Setup Instructions

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Gmail API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

### Step 2: Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in app name and your email
   - Add your email to "Test users"
4. Select "Desktop app" as application type
5. Download the JSON file
6. **Rename it to `credentials.json`** and place it in this project folder

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure the Application

Edit `config.py` and update:

```python
EMAIL_CONFIG = {
    'default_recipient': 'your-actual-email@gmail.com',  # Your email
}
```

### Step 5: Run the Application

```bash
python main.py
```

On first run, a browser window will open for Google authentication. Allow the permissions to send emails.

## Usage Examples

### Send a Simple Email

```python
from gmail_service import GmailService

gmail = GmailService()
gmail.authenticate()

gmail.send_email(
    to="recipient@example.com",
    subject="Test Email",
    body="Hello! This is a test email."
)
```

### Send HTML Email

```python
gmail.send_email(
    to="recipient@example.com",
    subject="HTML Email",
    body="<h1>Hello</h1><p>This is <b>HTML</b> content.</p>",
    html=True
)
```

### Send Email with Attachment

```python
gmail.send_email_with_attachment(
    to="recipient@example.com",
    subject="Email with File",
    body="Please find the attached file.",
    attachment_path="document.pdf"
)
```

### Quick Send (One-liner)

```python
from gmail_service import quick_send

quick_send("recipient@example.com", "Quick Hello", "This is a quick message!")
```

## File Structure

```
Gmail integration/
├── gmail_service.py    # Gmail API service module
├── main.py             # Main application script
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── credentials.json    # OAuth credentials (you add this)
├── token.json          # Auth token (auto-generated)
└── README.md           # This file
```

## Troubleshooting

### "credentials.json not found"
Download credentials from Google Cloud Console and place in project folder.

### "Access blocked: App has not completed the Google verification process"
This is normal for development. Click "Advanced" > "Go to [App Name] (unsafe)" to proceed.

### "RefreshError"
Delete `token.json` and run again to re-authenticate.

## Security Notes

- Never commit `credentials.json` or `token.json` to version control
- Add these files to `.gitignore`
- Keep your credentials secure

## License

MIT License
