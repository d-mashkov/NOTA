"""
Агент Артём — охотник за трендами в соцсетях.
Источники: TikTok, LinkedIn, YouTube через Exa
           X/Twitter через Grok Agent Tools API
           Reddit через PRAW (если есть ключи) + Grok web_search
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'), override=True)

_exa_client = None
_reddit_client = None


def _get_exa():
    global _exa_client
    if _exa_client is None:
        from exa_py import Exa
        _exa_client = Exa(api_key=os.getenv("EXA_API_KEY", ""))
    return _exa_client


def _get_reddit():
    """Ленивая инициализация PRAW. Возвращает None если нет credentials."""
    global _reddit_client
    if _reddit_client is not None:
        return _reddit_client
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None
    try:
        import praw
        _reddit_client = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="NOTA-FMCG-bot/1.0",
        )
        return _reddit_client
    except Exception as e:
        print(f"[Артём] Reddit PRAW init error: {e}")
        return None


# ──────────────────────────────────────────────
# Exa поиск
# ──────────────────────────────────────────────
def _exa_search(query: str, num: int = 5) -> list:
    try:
        result = _get_exa().search_and_contents(
            query,
            num_results=num,
            text={"max_characters": 600},
        )
        return result.results or []
    except Exception as e:
        print(f"[Артём] Exa error: {e}")
        return []


# ──────────────────────────────────────────────
# Grok — X/Twitter live search
# ──────────────────────────────────────────────
def _grok_request(prompt: str, tools: list = None) -> str:
    """Базовый запрос к Grok Agent Tools API."""
    key = os.getenv("GROK_API_KEY", "")
    if not key:
        return ""
    if tools is None:
        tools = [{"type": "x_search"}, {"type": "web_search"}]
    try:
        r = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "grok-4.3",
                "tools": tools,
                "input": [{"role": "user", "content": prompt}],
            },
            timeout=40,
        )
        r.raise_for_status()
        data = r.json()

        text_parts = []
        citations = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        text_parts.append(block.get("text", ""))
            elif item.get("type") == "web_search_results":
                for res in item.get("results", [])[:3]:
                    if res.get("url"):
                        citations.append(res["url"])

        text = "\n".join(text_parts).strip()
        if citations:
            text += "\n\n📎 Источники:\n" + "\n".join(f"  — {c}" for c in citations[:3])
        return text

    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        print(f"[Артём] Grok HTTP {status}: {e.response.text[:200] if e.response else e}")
        return ""
    except Exception as e:
        print(f"[Артём] Grok error: {e}")
        return ""


def _grok_search(query: str) -> str:
    """X/Twitter тренды через Grok live search."""
    return _grok_request(
        f"Найди свежие обсуждения в X/Twitter по теме: {query}\n\n"
        "Покажи на русском языке:\n"
        "• Что сейчас вирусится / хайпует в X\n"
        "• Тональность обсуждений (позитив/негатив/нейтрал)\n"
        "• Ключевые инфлюенсеры или бренды если есть\n"
        "• Вывод: есть ли реальный тренд в X-сообществе\n\n"
        "Максимум 300 слов.",
        tools=[{"type": "x_search"}, {"type": "web_search"}],
    )


# ──────────────────────────────────────────────
# Reddit — PRAW (официальный API)
# ──────────────────────────────────────────────

# FMCG-релевантные сабреддиты
FMCG_SUBREDDITS = [
    "CPGIndustry",      # Consumer Packaged Goods — профессионалы отрасли
    "food",             # еда в целом
    "nutrition",        # нутрициология
    "HealthyFood",      # здоровое питание
    "Entrepreneur",     # запуски продуктов
    "veganfitness",     # растительное питание
    "supplements",      # добавки и функциональное питание
]


def _reddit_via_praw(query: str) -> str:
    """Ищет в Reddit через PRAW (требует REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET)."""
    reddit = _get_reddit()
    if not reddit:
        return ""

    print("[Артём] Reddit PRAW поиск...")
    results = []
    try:
        for submission in reddit.subreddit("+".join(FMCG_SUBREDDITS)).search(
            query, sort="hot", time_filter="month", limit=8
        ):
            results.append({
                "title": submission.title,
                "subreddit": submission.subreddit.display_name,
                "score": submission.score,
                "url": f"https://reddit.com{submission.permalink}",
                "selftext": (submission.selftext or "")[:200],
            })
    except Exception as e:
        print(f"[Артём] PRAW search error: {e}")
        return ""

    if not results:
        return ""

    lines = [f"**Reddit (r/CPGIndustry, r/food и др.) — свежие обсуждения:**"]
    for r in sorted(results, key=lambda x: x["score"], reverse=True)[:5]:
        lines.append(
            f"• [{r['score']}★] **r/{r['subreddit']}** — {r['title']}\n"
            f"  {r['selftext'][:150]}\n"
            f"  🔗 {r['url']}"
        )
    return "\n".join(lines)


def _reddit_via_grok(query: str) -> str:
    """Ищет Reddit-дискуссии через Grok web_search (работает без credentials)."""
    return _grok_request(
        f"Search Reddit for recent discussions about: {query} in context of FMCG, food industry, consumer trends.\n\n"
        "Find posts from subreddits like r/CPGIndustry, r/food, r/nutrition, r/HealthyFood, r/Entrepreneur.\n"
        "Show in Russian:\n"
        "• Top 3-5 most upvoted/discussed posts (subreddit, title, key point)\n"
        "• Main sentiment and concerns\n"
        "• Any viral products or brands mentioned\n"
        "• Conclusion: what does Reddit think about this trend?\n\n"
        "Max 250 words.",
        tools=[{"type": "web_search"}],
    )


# ──────────────────────────────────────────────
# Главная функция
# ──────────────────────────────────────────────
def search_social_trends(query: str) -> str:
    """
    Ищет тренды: TikTok, LinkedIn, YouTube, X/Twitter (Grok), Reddit (PRAW + Grok).
    """
    print(f"[Артём] Поиск: {query}")
    parts = []

    # TikTok
    tiktok = _exa_search(f"site:tiktok.com {query} trending viral", num=5)
    if tiktok:
        parts.append("📱 **TikTok тренды:**")
        for r in tiktok[:4]:
            parts.append(f"• {r.title or r.url}\n  {(r.text or '')[:200]}")

    # LinkedIn
    linkedin = _exa_search(f"site:linkedin.com {query} FMCG consumer trend 2025 2026", num=5)
    if linkedin:
        parts.append("\n💼 **LinkedIn / Индустрия:**")
        for r in linkedin[:4]:
            parts.append(f"• {r.title or r.url}\n  {(r.text or '')[:200]}")

    # YouTube
    youtube = _exa_search(f"site:youtube.com {query} trend review новинки 2025", num=4)
    if youtube:
        parts.append("\n🎥 **YouTube:**")
        for r in youtube[:3]:
            parts.append(f"• {r.title or r.url}")

    # X/Twitter через Grok
    print("[Артём] X/Twitter через Grok...")
    grok_result = _grok_search(query)
    if grok_result:
        parts.append(f"\n🐦 **X/Twitter (Grok live):**\n{grok_result}")

    # Reddit — сначала PRAW, потом Grok как fallback
    print("[Артём] Reddit...")
    reddit_result = _reddit_via_praw(query)
    if not reddit_result:
        reddit_result = _reddit_via_grok(query)
    if reddit_result:
        parts.append(f"\n🟠 **Reddit:**\n{reddit_result}")

    if not parts:
        return "Артём: данных по запросу не найдено."

    return "\n".join(parts)
