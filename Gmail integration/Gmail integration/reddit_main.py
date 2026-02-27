"""
Reddit Automation - Main Script
Auto-post to Reddit subreddits
"""

from reddit_service import RedditService, quick_post
from reddit_config import REDDIT_CONFIG, POSTING_CONFIG


def post_hello_world():
    """Post a simple Hello World test to r/test"""
    reddit = RedditService()
    
    if not reddit.authenticate():
        print("❌ Authentication failed. Check your credentials in reddit_config.py")
        return None
    
    # Post to r/test (Reddit's official testing subreddit)
    result = reddit.post_text(
        subreddit_name='test',
        title='Hello World - Reddit Automation Test',
        body='''Hello World!

This is a test post from my Reddit Automation System.

If you're seeing this, the integration is working successfully! 🎉

---
*Posted automatically using PRAW (Python Reddit API Wrapper)*'''
    )
    
    if result:
        print("\n✅ Hello World post created successfully!")
        print(f"   View it at: {result.url}")
    else:
        print("\n❌ Failed to create post")
    
    return result


def post_to_subreddit(subreddit, title, body):
    """
    Post content to a specific subreddit
    
    Args:
        subreddit: Subreddit name (without r/)
        title: Post title
        body: Post content
    """
    reddit = RedditService()
    
    if not reddit.authenticate():
        print("❌ Authentication failed")
        return None
    
    return reddit.post_text(subreddit, title, body)


def check_subreddit(subreddit_name):
    """Check info about a subreddit before posting"""
    reddit = RedditService()
    
    if not reddit.authenticate():
        return None
    
    info = reddit.get_subreddit_info(subreddit_name)
    
    if info:
        print(f"\n📋 Subreddit Info: r/{info['name']}")
        print(f"   Title: {info['title']}")
        print(f"   Subscribers: {info['subscribers']:,}")
        print(f"   Type: {info['type']}")
        print(f"   NSFW: {info['nsfw']}")
        print(f"   Description: {info['description'][:100]}...")
    
    return info


def main():
    """Main function - demonstrates Reddit posting capabilities"""
    print("=" * 50)
    print("Reddit Automation System")
    print("=" * 50)
    print()
    
    # Check if config is set up
    if REDDIT_CONFIG['client_id'] == 'YOUR_CLIENT_ID':
        print("⚠️  Please update reddit_config.py with your Reddit API credentials first!")
        print()
        print("Steps to get credentials:")
        print("1. Go to https://www.reddit.com/prefs/apps")
        print("2. Click 'create another app...'")
        print("3. Choose 'script' type")
        print("4. Copy client_id and client_secret to reddit_config.py")
        print("5. Add your Reddit username and password")
        return
    
    print("Posting Hello World to r/test...")
    print()
    post_hello_world()


if __name__ == "__main__":
    main()
