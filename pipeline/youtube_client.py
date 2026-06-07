import requests
from pipeline.config import YOUTUBE_API_KEY

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"


def search_youtube(query: str, max_results: int = 10) -> list[dict]:
    """Ищет видео на YouTube по запросу, возвращает список с метриками."""
    if not YOUTUBE_API_KEY:
        return []

    # Поиск видео
    resp = requests.get(YOUTUBE_API_URL, params={
        "key": YOUTUBE_API_KEY,
        "q": query,
        "type": "video",
        "part": "snippet",
        "maxResults": max_results,
        "order": "relevance",
        "relevanceLanguage": "ru",
        "publishedAfter": "2024-01-01T00:00:00Z",
    }, timeout=15)

    if resp.status_code != 200:
        return []

    items = resp.json().get("items", [])
    if not items:
        return []

    # Получим статистику (просмотры, лайки)
    video_ids = ",".join(i["id"]["videoId"] for i in items)
    stats_resp = requests.get(YOUTUBE_VIDEO_URL, params={
        "key": YOUTUBE_API_KEY,
        "id": video_ids,
        "part": "statistics",
    }, timeout=15)

    stats_map = {}
    if stats_resp.status_code == 200:
        for v in stats_resp.json().get("items", []):
            stats_map[v["id"]] = v.get("statistics", {})

    results = []
    for item in items:
        vid_id = item["id"]["videoId"]
        snippet = item["snippet"]
        stats = stats_map.get(vid_id, {})
        results.append({
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:300],
            "channel": snippet.get("channelTitle", ""),
            "published": snippet.get("publishedAt", "")[:10],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "url": f"https://youtube.com/watch?v={vid_id}",
        })

    return sorted(results, key=lambda x: x["views"], reverse=True)


def format_youtube_for_prompt(results: list[dict]) -> str:
    """Форматирует YouTube данные для промпта."""
    if not results:
        return ""

    lines = []
    for r in results[:8]:
        views_fmt = f"{r['views']:,}".replace(",", " ")
        lines.append(
            f"[YouTube | {r['published']} | 👁 {views_fmt} просмотров]\n"
            f"«{r['title']}» — {r['channel']}\n"
            f"{r['description']}\n"
            f"URL: {r['url']}"
        )
    return "\n\n".join(lines)
