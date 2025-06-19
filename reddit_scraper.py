import praw
import os

# Load credentials from environment variables or define directly
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', 'vXUKfL-6ZZ7UvDJqQ3h1hA')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', 'IkxKZlg-fJETIuNdgyBJxa2YDMpaZA')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'parsewithme_app by u/your_username')

# Initialize Reddit instance using PRAW
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

def fetch_reddit_posts(keyword, limit=10):
    try:
        results = []
        for submission in reddit.subreddit("all").search(keyword, limit=limit):
            results.append({
                "title": submission.title,
                "url": f"https://www.reddit.com{submission.permalink}"
            })
        return results
    except Exception as e:
        print(f"Error fetching Reddit posts: {e}")
        return []
