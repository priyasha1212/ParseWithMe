import requests

def fetch_reddit_posts(keyword):
    url = f"https://www.reddit.com/search.json?q={keyword}&limit=10"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        posts = []
        for post in data["data"]["children"]:
            title = post["data"]["title"]
            url = "https://www.reddit.com" + post["data"]["permalink"]
            posts.append({"title": title, "url": url})
        return posts
    else:
        return []
