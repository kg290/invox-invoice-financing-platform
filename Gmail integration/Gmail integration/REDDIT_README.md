# Reddit Automation System

A Python-based Reddit integration for auto-posting to subreddits using PRAW.

## Features

- ✅ Post text content to subreddits
- ✅ Post links to subreddits
- ✅ Post images to subreddits
- ✅ Check subreddit information
- ✅ OAuth script authentication

## Setup Instructions

### Step 1: Create Reddit App

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Scroll down and click **"create another app..."**
3. Fill in the form:
   - **name**: Your app name (e.g., "WhistleChain Bot")
   - **App type**: Select **"script"**
   - **description**: Brief description
   - **redirect uri**: `http://localhost:8080`
4. Click **"create app"**
5. Note down:
   - **client_id**: The string under your app name (looks like: `AbCdEfGhIjKlMn`)
   - **client_secret**: Listed as "secret"

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Credentials

Edit `reddit_config.py`:

```python
REDDIT_CONFIG = {
    'client_id': 'YOUR_CLIENT_ID',          # From step 1
    'client_secret': 'YOUR_CLIENT_SECRET',  # From step 1
    'username': 'YOUR_REDDIT_USERNAME',     # Your Reddit username
    'password': 'YOUR_REDDIT_PASSWORD',     # Your Reddit password
    'user_agent': 'MyBot v1.0 by YOUR_USERNAME',
}
```

### Step 4: Run the Application

```bash
python reddit_main.py
```

This will post a "Hello World" test message to r/test.

## Usage Examples

### Post Text to a Subreddit

```python
from reddit_service import RedditService

reddit = RedditService()
reddit.authenticate()

reddit.post_text(
    subreddit_name='test',
    title='My Post Title',
    body='This is the content of my post.'
)
```

### Post a Link

```python
reddit.post_link(
    subreddit_name='test',
    title='Check out this link!',
    url='https://example.com'
)
```

### Post an Image

```python
reddit.post_image(
    subreddit_name='test',
    title='My Image Post',
    image_path='image.png'
)
```

### Quick Post (One-liner)

```python
from reddit_service import quick_post

quick_post('test', 'Quick Title', 'Quick body text!')
```

### Get Subreddit Info

```python
reddit = RedditService()
reddit.authenticate()

info = reddit.get_subreddit_info('python')
print(f"Subscribers: {info['subscribers']}")
```

## File Structure

```
Gmail integration/
├── reddit_service.py   # Reddit API service module
├── reddit_main.py      # Main Reddit script
├── reddit_config.py    # Reddit configuration
├── gmail_service.py    # Gmail API service module
├── main.py             # Main Gmail script
├── config.py           # Gmail configuration
├── requirements.txt    # All dependencies
└── README.md           # Gmail setup guide
```

## Important Notes

### Rate Limiting
Reddit has rate limits. Don't spam posts - wait at least 10 seconds between posts.

### Testing
Always use **r/test** for testing. It's Reddit's official testing subreddit.

### Subreddit Rules
Each subreddit has its own posting rules. Check rules before auto-posting.

### Account Age
New Reddit accounts have posting restrictions. Use an established account.

## Troubleshooting

### "Invalid credentials"
- Double-check client_id and client_secret
- Ensure username/password are correct
- Check if 2FA is enabled (disable or use app password)

### "Received 403 HTTP response"
- Your account may be too new
- You might be rate-limited
- The subreddit may have restrictions

### "Forbidden" when posting
- Check if you're subscribed to the subreddit
- Some subreddits require karma to post
- Check subreddit posting rules

## Security Notes

- Never commit `reddit_config.py` with real credentials
- Consider using environment variables for passwords
- The `.gitignore` file already excludes sensitive files

## License

MIT License
