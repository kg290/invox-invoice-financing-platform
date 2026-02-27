"""
Configuration file for Gmail Automation System
Loads credentials from .env file for security
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Email Configuration
EMAIL_CONFIG = {
    'default_recipient': os.getenv('GMAIL_DEFAULT_RECIPIENT', 'karnajeet.gosavi23@vit.edu'),
    'sender_name': os.getenv('GMAIL_SENDER_NAME', 'WhistleChain Notification System'),
}

# Notification settings
NOTIFICATION_CONFIG = {
    'recipients': os.getenv('NOTIFICATION_RECIPIENTS', 'karnajeet.gosavi23@vit.edu').split(','),
    
    'templates': {
        'alert': {
            'subject_prefix': '[ALERT]',
            'priority': 'high',
        },
        'info': {
            'subject_prefix': '[INFO]',
            'priority': 'normal',
        },
        'reminder': {
            'subject_prefix': '[REMINDER]',
            'priority': 'normal',
        },
    }
}

# Path settings
PATHS = {
    'credentials_file': os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json'),
    'token_file': os.getenv('GMAIL_TOKEN_FILE', 'token.json'),
}
