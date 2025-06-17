from googleapiclient.discovery import build

def fetch_youtube_videos(keyword, api_key, max_results=10):
    youtube = build("youtube", "v3", developerKey=api_key)
    request = youtube.search().list(
        q=keyword,
        part="snippet",
        type="video",
        maxResults=max_results
    )
    response = request.execute()

    results = []
    for item in response.get("items", []):
        results.append({
            "title": item["snippet"]["title"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        })

    return results
