import requests

def fetch_reddit_posts(keyword):
    base_url = f"https://www.reddit.com/search.json?q={keyword}&limit=10"
    proxy_url = f"https://cors-anywhere.herokuapp.com/{base_url}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)',
        'Origin': 'https://render.com',
        'Referer': 'https://render.com'
    }

    try:
        response = requests.get(proxy_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            posts = []
            for post in data["data"]["children"]:
                title = post["data"]["title"]
                url = "https://www.reddit.com" + post["data"]["permalink"]
                posts.append({"title": title, "url": url})
            return posts
        else:
            print(f"Reddit proxy error: {response.status_code}")
            print(response.text)
            return []
    except Exception as e:
        print(f"Reddit fetch error: {e}")
        return []
