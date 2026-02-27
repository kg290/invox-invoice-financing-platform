"""
Reddit Service Module
Handles Reddit API authentication and posting operations using PRAW
"""

import praw
from prawcore.exceptions import PrawcoreException
from reddit_config import REDDIT_CONFIG


class RedditService:
    """Reddit API Service class for posting and interacting with Reddit"""
    
    def __init__(self):
        """Initialize Reddit Service with credentials from config"""
        self.reddit = None
        self.authenticated = False
        
    def authenticate(self):
        """
        Authenticate with Reddit API using OAuth credentials
        
        Returns:
            bool: True if authentication successful
        """
        try:
            self.reddit = praw.Reddit(
                client_id=REDDIT_CONFIG['client_id'],
                client_secret=REDDIT_CONFIG['client_secret'],
                user_agent=REDDIT_CONFIG['user_agent'],
                username=REDDIT_CONFIG['username'],
                password=REDDIT_CONFIG['password']
            )
            
            # Verify authentication by accessing user identity
            username = self.reddit.user.me().name
            print(f"✅ Authenticated as: u/{username}")
            self.authenticated = True
            return True
            
        except PrawcoreException as e:
            print(f"❌ Authentication failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            return False
    
    def post_text(self, subreddit_name, title, body, flair=None):
        """
        Create a text post in a subreddit
        
        Args:
            subreddit_name: Name of subreddit (without r/)
            title: Post title
            body: Post body content (self text)
            flair: Optional flair text
            
        Returns:
            praw.models.Submission: The created post or None if failed
        """
        if not self.authenticated:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Check if subreddit exists and allows posting
            if subreddit.subreddit_type == 'private':
                print(f"❌ r/{subreddit_name} is a private subreddit")
                return None
            
            submission = subreddit.submit(
                title=title,
                selftext=body,
                flair_id=flair
            )
            
            print(f"✅ Post created successfully!")
            print(f"   Title: {title}")
            print(f"   Subreddit: r/{subreddit_name}")
            print(f"   URL: {submission.url}")
            
            return submission
            
        except PrawcoreException as e:
            print(f"❌ Failed to create post: {e}")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def post_link(self, subreddit_name, title, url, flair=None):
        """
        Create a link post in a subreddit
        
        Args:
            subreddit_name: Name of subreddit (without r/)
            title: Post title
            url: URL to share
            flair: Optional flair text
            
        Returns:
            praw.models.Submission: The created post or None if failed
        """
        if not self.authenticated:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            submission = subreddit.submit(
                title=title,
                url=url,
                flair_id=flair
            )
            
            print(f"✅ Link post created successfully!")
            print(f"   Title: {title}")
            print(f"   Link: {url}")
            print(f"   Subreddit: r/{subreddit_name}")
            print(f"   Post URL: {submission.url}")
            
            return submission
            
        except PrawcoreException as e:
            print(f"❌ Failed to create link post: {e}")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def post_image(self, subreddit_name, title, image_path, flair=None):
        """
        Create an image post in a subreddit
        
        Args:
            subreddit_name: Name of subreddit (without r/)
            title: Post title
            image_path: Path to image file
            flair: Optional flair text
            
        Returns:
            praw.models.Submission: The created post or None if failed
        """
        if not self.authenticated:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            submission = subreddit.submit_image(
                title=title,
                image_path=image_path,
                flair_id=flair
            )
            
            print(f"✅ Image post created successfully!")
            print(f"   Title: {title}")
            print(f"   Subreddit: r/{subreddit_name}")
            print(f"   URL: {submission.url}")
            
            return submission
            
        except PrawcoreException as e:
            print(f"❌ Failed to create image post: {e}")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def get_subreddit_info(self, subreddit_name):
        """
        Get information about a subreddit
        
        Args:
            subreddit_name: Name of subreddit (without r/)
            
        Returns:
            dict: Subreddit information
        """
        if not self.authenticated:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            info = {
                'name': subreddit.display_name,
                'title': subreddit.title,
                'subscribers': subreddit.subscribers,
                'description': subreddit.public_description,
                'type': subreddit.subreddit_type,
                'nsfw': subreddit.over18,
                'created_utc': subreddit.created_utc,
            }
            
            return info
            
        except Exception as e:
            print(f"❌ Error getting subreddit info: {e}")
            return None
    
    def check_can_post(self, subreddit_name):
        """
        Check if user can post to a subreddit
        
        Args:
            subreddit_name: Name of subreddit
            
        Returns:
            bool: True if user can post
        """
        if not self.authenticated:
            return False
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            # Check if we can submit
            return subreddit.user_is_subscriber or subreddit.subreddit_type == 'public'
        except:
            return False


def quick_post(subreddit, title, body):
    """
    Quick function to post without managing service instance
    
    Args:
        subreddit: Subreddit name
        title: Post title
        body: Post content
        
    Returns:
        praw.models.Submission or None
    """
    reddit = RedditService()
    if reddit.authenticate():
        return reddit.post_text(subreddit, title, body)
    return None
