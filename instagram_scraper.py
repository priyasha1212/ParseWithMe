import requests
import json
from typing import List, Dict, Optional

class InstagramScraper:
    def __init__(self):
        self.base_url = "https://instagram120.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-host': 'instagram120.p.rapidapi.com',
            'x-rapidapi-key': '69f4c3bce7mshc90021bf41b07a1p1aaaaejsna9b49e5c2914'
        }
    
    def search_hashtag(self, hashtag: str, limit: int = 10) -> List[Dict]:
        """
        Search Instagram posts by hashtag
        
        Args:
            hashtag (str): The hashtag to search for (without #)
            limit (int): Maximum number of posts to return
            
        Returns:
            List[Dict]: List of Instagram posts with their details
        """
        try:
            # Remove # if user includes it
            hashtag = hashtag.lstrip('#')
            
            url = f"{self.base_url}/hashtag/{hashtag}"
            params = {"count": limit}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the response and extract relevant information
            posts = []
            
            if 'data' in data and isinstance(data['data'], list):
                for item in data['data'][:limit]:
                    post = {
                        'id': str(item.get('id', '')),
                        'shortcode': item.get('shortcode', ''),
                        'url': f"https://www.instagram.com/p/{item.get('shortcode', '')}/",
                        'caption': item.get('caption', ''),
                        'likes': item.get('like_count', 0),
                        'comments': item.get('comment_count', 0),
                        'timestamp': item.get('timestamp', 0),
                        'is_video': item.get('is_video', False),
                        'display_url': item.get('display_url', ''),
                        'owner_username': item.get('owner', {}).get('username', 'Unknown')
                    }
                    posts.append(post)
            
            return posts
            
        except requests.exceptions.RequestException as e:
            print(f"Request error while searching hashtag '{hashtag}': {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON decode error while searching hashtag '{hashtag}': {e}")
            return []
        except Exception as e:
            print(f"Unexpected error while searching hashtag '{hashtag}': {e}")
            return []
    
    def _extract_caption(self, node: Dict) -> str:
        """Extract caption text from post node"""
        try:
            if 'edge_media_to_caption' in node:
                edges = node['edge_media_to_caption']['edges']
                if edges:
                    return edges[0]['node']['text']
            return ""
        except (KeyError, IndexError):
            return ""
    
    def search_user_posts(self, username: str, limit: int = 10) -> List[Dict]:
        """
        Search Instagram posts by username (if API supports it)
        This is a placeholder - you may need to implement based on available endpoints
        """
        # This would require a different endpoint from the RapidAPI
        # For now, returning empty list as the current API seems hashtag-focused
        return []

# Convenience function for easy import
def fetch_instagram_posts(hashtag: str, limit: int = 10) -> List[Dict]:
    """
    Fetch Instagram posts for a given hashtag
    
    Args:
        hashtag (str): The hashtag to search for
        limit (int): Maximum number of posts to return
        
    Returns:
        List[Dict]: List of Instagram posts
    """
    scraper = InstagramScraper()
    return scraper.search_hashtag(hashtag, limit)