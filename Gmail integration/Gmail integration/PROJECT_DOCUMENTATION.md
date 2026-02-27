# WhistleChain - Social Media Integration Documentation

**Project:** Gmail & Reddit Automation System  
**Version:** 1.1  
**Last Updated:** February 20, 2026

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [File Structure](#file-structure)
3. [Environment Variables (.env)](#environment-variables-env)
4. [Dependencies](#dependencies)
5. [Gmail Integration](#gmail-integration)
6. [Reddit Integration](#reddit-integration)
7. [Integration with Other Projects](#integration-with-other-projects)
8. [API Reference](#api-reference)
9. [Credentials Summary](#credentials-summary)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

This project provides automated social media integration for the **WhistleChain** system, enabling:

- **Gmail**: Send automated email notifications, alerts, and updates
- **Reddit**: Auto-post content to subreddits

### Key Features

| Platform | Features |
|----------|----------|
| Gmail | Send emails, HTML emails, attachments, notifications |
| Reddit | Post text, links, images to subreddits |

---

## File Structure

```
Gmail integration/
│
├── 🔐 CONFIGURATION
│   ├── .env                  # Environment variables (CREATE THIS - DO NOT COMMIT)
│   ├── .env.example          # Template for .env file
│   ├── config.py             # Gmail configuration (reads from .env)
│   └── reddit_config.py      # Reddit configuration (reads from .env)
│
├── 📧 GMAIL INTEGRATION
│   ├── gmail_service.py      # Gmail API service module
│   ├── main.py               # Main Gmail script
│   ├── credentials.json      # Google OAuth credentials (DO NOT SHARE)
│   └── token.json            # Auth token (auto-generated)
│
├── 🔴 REDDIT INTEGRATION
│   ├── reddit_service.py     # Reddit API service module
│   └── reddit_main.py        # Main Reddit script
│
├── 📄 DOCUMENTATION
│   ├── README.md             # Gmail setup guide
│   ├── REDDIT_README.md      # Reddit setup guide
│   └── PROJECT_DOCUMENTATION.md  # This file
│
├── requirements.txt          # Python dependencies
└── .gitignore               # Git ignore rules
```

---

## Environment Variables (.env)

All sensitive credentials are stored in a `.env` file for security.

### Setup Instructions

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials

### .env File Template

```env
# ===========================================
# WhistleChain Social Media Integration
# ===========================================

# ============ GMAIL CONFIGURATION ============
GMAIL_DEFAULT_RECIPIENT=your-email@example.com
GMAIL_SENDER_NAME=WhistleChain Notification System
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json

# ============ REDDIT CONFIGURATION ============
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT=WhistleChain AutoPoster v1.0 by your_username
REDDIT_DEFAULT_SUBREDDIT=test

# ============ NOTIFICATION SETTINGS ============
NOTIFICATION_RECIPIENTS=email1@example.com,email2@example.com

# ============ OPTIONAL SETTINGS ============
REDDIT_POST_DELAY=10
REDDIT_MAX_POSTS=5
```

### Environment Variable Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `GMAIL_DEFAULT_RECIPIENT` | Default email recipient | - |
| `GMAIL_SENDER_NAME` | Sender display name | WhistleChain Notification System |
| `GMAIL_CREDENTIALS_FILE` | Path to Google OAuth file | credentials.json |
| `GMAIL_TOKEN_FILE` | Path to store OAuth token | token.json |
| `REDDIT_CLIENT_ID` | Reddit app client ID | - |
| `REDDIT_CLIENT_SECRET` | Reddit app secret | - |
| `REDDIT_USERNAME` | Reddit account username | - |
| `REDDIT_PASSWORD` | Reddit account password | - |
| `REDDIT_USER_AGENT` | Reddit API user agent | WhistleChain AutoPoster v1.0 |
| `REDDIT_DEFAULT_SUBREDDIT` | Default subreddit for posts | test |
| `NOTIFICATION_RECIPIENTS` | Comma-separated email list | - |
| `REDDIT_POST_DELAY` | Seconds between posts | 10 |
| `REDDIT_MAX_POSTS` | Max posts per session | 5 |

---

## Dependencies

### Install All Dependencies

```bash
pip install -r requirements.txt
```

### Required Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `google-api-python-client` | ≥2.100.0 | Gmail API |
| `google-auth-httplib2` | ≥0.1.1 | Gmail authentication |
| `google-auth-oauthlib` | ≥1.1.0 | Gmail OAuth flow |
| `praw` | ≥7.7.0 | Reddit API wrapper |
| `python-dotenv` | ≥1.0.0 | Environment variables |

---

## Gmail Integration

### Credentials Required

| Credential | Source | Storage |
|------------|--------|---------|
| OAuth Client ID | Google Cloud Console | `credentials.json` |
| OAuth Client Secret | Google Cloud Console | `credentials.json` |
| Access Token | Auto-generated | `token.json` |
| Recipient Email | Your configuration | `.env` file |

### Current Configuration (from .env)

```python
# config.py - Loads from .env
EMAIL_CONFIG = {
    'default_recipient': os.getenv('GMAIL_DEFAULT_RECIPIENT'),
    'sender_name': os.getenv('GMAIL_SENDER_NAME'),
}
```

### How to Get Gmail Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Gmail API** (APIs & Services → Library)
4. Create **OAuth 2.0 credentials** (APIs & Services → Credentials)
   - Application type: Desktop app
5. Download JSON and save as `credentials.json`
6. Configure OAuth consent screen:
   - Add test users
   - Set scopes: `https://www.googleapis.com/auth/gmail.send`

### Gmail API Scope

```python
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
```

---

## Reddit Integration

### Credentials Required

| Credential | Source | Storage |
|------------|--------|---------|
| Client ID | Reddit App Settings | `.env` file |
| Client Secret | Reddit App Settings | `.env` file |
| Username | Your Reddit account | `.env` file |
| Password | Your Reddit account | `.env` file |

### Current Configuration (from .env)

```python
# reddit_config.py - Loads from .env
REDDIT_CONFIG = {
    'client_id': os.getenv('REDDIT_CLIENT_ID'),
    'client_secret': os.getenv('REDDIT_CLIENT_SECRET'),
    'username': os.getenv('REDDIT_USERNAME'),
    'password': os.getenv('REDDIT_PASSWORD'),
    'user_agent': os.getenv('REDDIT_USER_AGENT'),
}
```

### How to Get Reddit Credentials

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Click **"create another app..."**
3. Fill in:
   - **Name**: WhistleChain Bot
   - **Type**: script
   - **Redirect URI**: `http://localhost:8080`
4. Copy:
   - **Client ID**: Under app name (e.g., `AbCdEfGhIjKlMn`)
   - **Client Secret**: Listed as "secret"
5. Add to your `.env` file

---

## Integration with Other Projects

### Option 1: Import as Module

Copy these files to your project:

```
your_project/
├── services/
│   ├── gmail_service.py
│   ├── reddit_service.py
│   ├── config.py
│   └── reddit_config.py
├── .env                  # Your environment variables
├── credentials.json      # Gmail OAuth credentials
└── your_main.py
```

Then import:

```python
from services.gmail_service import GmailService, quick_send
from services.reddit_service import RedditService, quick_post
```

### Option 2: Direct Import (Same Directory)

```python
# Import Gmail
from gmail_service import GmailService

# Import Reddit
from reddit_service import RedditService
```

### Option 3: Package Installation

Create `setup.py`:

```python
from setuptools import setup, find_packages

setup(
    name='whistlechain-social',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'google-api-python-client>=2.100.0',
        'google-auth-httplib2>=0.1.1',
        'google-auth-oauthlib>=1.1.0',
        'praw>=7.7.0',
    ],
)
```

Then install:
```bash
pip install -e .
```

---

## API Reference

### Gmail Service

#### Initialize & Authenticate

```python
from gmail_service import GmailService

gmail = GmailService()
gmail.authenticate()
```

#### Send Plain Text Email

```python
gmail.send_email(
    to='recipient@example.com',
    subject='Subject Line',
    body='Email body text'
)
```

#### Send HTML Email

```python
gmail.send_email(
    to='recipient@example.com',
    subject='HTML Email',
    body='<h1>Hello</h1><p>HTML content</p>',
    html=True
)
```

#### Send Email with Attachment

```python
gmail.send_email_with_attachment(
    to='recipient@example.com',
    subject='With Attachment',
    body='Please see attached.',
    attachment_path='document.pdf'
)
```

#### Quick Send (One-liner)

```python
from gmail_service import quick_send

quick_send('recipient@example.com', 'Subject', 'Body')
```

---

### Reddit Service

#### Initialize & Authenticate

```python
from reddit_service import RedditService

reddit = RedditService()
reddit.authenticate()
```

#### Post Text

```python
reddit.post_text(
    subreddit_name='test',
    title='Post Title',
    body='Post content here'
)
```

#### Post Link

```python
reddit.post_link(
    subreddit_name='test',
    title='Check this out',
    url='https://example.com'
)
```

#### Post Image

```python
reddit.post_image(
    subreddit_name='test',
    title='Image Post',
    image_path='image.png'
)
```

#### Quick Post (One-liner)

```python
from reddit_service import quick_post

quick_post('test', 'Title', 'Body content')
```

#### Get Subreddit Info

```python
info = reddit.get_subreddit_info('python')
print(info['subscribers'])
```

---

## Credentials Summary

### Gmail Credentials

| Item | Value/Location |
|------|----------------|
| OAuth Type | Desktop Application |
| Credentials File | `credentials.json` |
| Token File | `token.json` |
| API Scope | `gmail.send` |
| Console URL | https://console.cloud.google.com/ |
| Config Storage | `.env` file |

### Reddit Credentials

| Item | Value/Location |
|------|----------------|
| App Type | Script |
| Redirect URI | `http://localhost:8080` |
| App Settings URL | https://www.reddit.com/prefs/apps |
| Config Storage | `.env` file |

### .env Credentials Reference

```env
# Gmail
GMAIL_DEFAULT_RECIPIENT=your-email@example.com
GMAIL_SENDER_NAME=WhistleChain Notification System

# Reddit
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=WhistleChain AutoPoster v1.0

# Notifications
NOTIFICATION_RECIPIENTS=email1@example.com,email2@example.com
```

### Security Notes

⚠️ **NEVER commit these files to version control:**

- `.env`
- `credentials.json`
- `token.json`

✅ These are already in `.gitignore`

---

## Troubleshooting

### Gmail Issues

| Error | Solution |
|-------|----------|
| `credentials.json not found` | Download from Google Cloud Console |
| `Access blocked` | Click "Advanced" → "Go to app (unsafe)" |
| `RefreshError` | Delete `token.json` and re-authenticate |
| `Insufficient permission` | Check OAuth scope includes `gmail.send` |

### Reddit Issues

| Error | Solution |
|-------|----------|
| `Invalid credentials` | Verify client_id and client_secret |
| `403 Forbidden` | Account too new or rate-limited |
| `OAuthException` | Check username/password; disable 2FA |
| `Received 429` | Rate limited - wait before posting |

---

## Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file from template
cp .env.example .env

# 3. Edit .env with your credentials
# (Use your preferred editor)

# 4. Test Gmail
python main.py

# 5. Test Reddit
python reddit_main.py
```

---

## Contact & Support

**Project:** WhistleChain  
**Module:** Social Media Integration  
**Maintainer:** karnajeet.gosavi23@vit.edu

---

*This documentation is auto-generated. Keep credentials secure.*
