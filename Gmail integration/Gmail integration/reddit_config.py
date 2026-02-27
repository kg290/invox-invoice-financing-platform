"""
Configuration file for Reddit Automation System
Loads credentials from .env file for security

HOW TO GET CREDENTIALS:
1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app..." at the bottom
3. Choose "script" as the app type
4. Fill in name and description
5. Set redirect uri to: http://localhost:8080
6. Copy client_id (under the app name) and client_secret
7. Add credentials to .env file
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Reddit API Configuration
REDDIT_CONFIG = {
    'client_id': os.getenv('REDDIT_CLIENT_ID', 'YOUR_CLIENT_ID'),
    'client_secret': os.getenv('REDDIT_CLIENT_SECRET', 'YOUR_CLIENT_SECRET'),
    'username': os.getenv('REDDIT_USERNAME', 'YOUR_REDDIT_USERNAME'),
    'password': os.getenv('REDDIT_PASSWORD', 'YOUR_REDDIT_PASSWORD'),
    'user_agent': os.getenv('REDDIT_USER_AGENT', 'WhistleChain AutoPoster v1.0'),
}

# Posting Configuration
POSTING_CONFIG = {
    'default_subreddit': os.getenv('REDDIT_DEFAULT_SUBREDDIT', 'test'),
    
    'target_subreddits': [
        # 'test',           # Reddit's official test subreddit
        # 'your_subreddit',
    ],
    
    'post_delay': int(os.getenv('REDDIT_POST_DELAY', '10')),
    'max_posts_per_session': int(os.getenv('REDDIT_MAX_POSTS', '5')),
}

# Templates for automated posts
POST_TEMPLATES = {
    'announcement': {
        'title_prefix': '[Announcement]',
        'flair': None,
    },
    'update': {
        'title_prefix': '[Update]',
        'flair': None,
    },
    'discussion': {
        'title_prefix': '[Discussion]',
        'flair': None,
    },
}
