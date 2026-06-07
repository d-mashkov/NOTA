"""
Еженедельный парсинг трендов из LinkedIn и Reddit через Exa.ai.
Сохраняет топ-10 сигналов в таблицу trend_signals.
"""
import requests
import json
from datetime import date, datetime
from pipeline.config import EXA_API_KEY, EXA_API_URL
from pipeline.supabase_client import supabase


# Запросы для поиска новых FMCG продуктов
SEARCH_QUERIES = [
    # LinkedIn
    {"query": "new FMCG product launch Russia 2025 consumer goods", "source": "linkedin", "domain": "linkedin.com"},
    {"query": "food beverage trend emerging market 2025 launch", "source": "linkedin", "domain": "linkedin.com"},
    {"query": "новый продукт FMCG Россия запуск рынок 2025", "source": "linkedin", "domain": "linkedin.com"},

    # Reddit
    {"query": "new food product trend what should exist consumer demand", "source": "reddit", "domain": "reddit.com"},
    {"query": "healthy snack drink product idea market gap FMCG", "source": "reddit", "domain": "reddit.com"},
    {"query": "functional food beverage trend 2025 reddit community", "source": "reddit", "domain": "reddit.com"},
    {"query": "что хочет потребитель новый продукт питания идея", "source": "reddit", "domain": "reddit.com"},
]


def _exa_fetch(query: str, domain: str, num_results: int = 5) -> list[dict]:
    try:
        resp = requests.post(EXA_API_URL, json={
            "query": query,
            "numResults": num_results,
            "includeDomains": [domain],
            "contents": {"text": {"maxCharacters": 600}},
            "type": "neural",
        }, headers={"x-api-key": EXA_API_KEY}, timeout=20)
        if resp.status_code == 200:
            return resp.json().get("results", [])
    except Exception as e:
        print(f"    ⚠️  Exa error: {e}")
    return []


def _score_result(result: dict) -> float:
    """Простая эвристика релевантности — по длине текста и ключевым словам."""
    text = (result.get("text") or "") + " " + (result.get("title") or "")
    text_lower = text.lower()

    score = len(text) / 100  # базовый балл за объём контента

    boost_words = [
        "launch", "new product", "trend", "demand", "growing", "market gap",
        "запуск", "новый продукт", "тренд", "спрос", "рынок", "идея",
        "functional", "healthy", "organic", "plant-based", "fmcg",
    ]
    for w in boost_words:
        if w in text_lower:
            score += 2

    return round(score, 1)


def fetch_and_save_news(dry_run: bool = False) -> int:
    """
    Собирает тренды из LinkedIn и Reddit, сохраняет топ-10 в trend_signals.
    Возвращает количество сохранённых сигналов.
    """
    print("📰 Fetching news signals...")
    today = date.today()
    all_results = []

    for q in SEARCH_QUERIES:
        print(f"  🔍 {q['source']}: {q['query'][:60]}...")
        results = _exa_fetch(q["query"], q["domain"])
        for r in results:
            r["_source"] = q["source"]
            r["_score"] = _score_result(r)
        all_results.extend(results)

    # Дедупликация по URL
    seen = set()
    unique = []
    for r in all_results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)

    # Топ-10 по score
    top10 = sorted(unique, key=lambda x: x.get("_score", 0), reverse=True)[:10]
    print(f"  📊 Total fetched: {len(all_results)} → unique: {len(unique)} → top: {len(top10)}")

    if dry_run:
        for i, r in enumerate(top10, 1):
            print(f"  [{i}] [{r['_source']}] {r.get('title','')[:70]}")
        return len(top10)

    # Удаляем старые сигналы типа linkedin/reddit (перезапишем свежими)
    supabase.table("trend_signals") \
        .delete() \
        .in_("source", ["linkedin", "reddit"]) \
        .execute()

    # Сохраняем новые
    saved = 0
    for r in top10:
        source = r.get("_source", "unknown")
        title = (r.get("title") or "")[:200]
        text = (r.get("text") or "")[:800]
        url = r.get("url", "")

        supabase.table("trend_signals").insert({
            "source": source,
            "keyword": title,
            "keyword_en": title,
            "country": "global",
            "value": r.get("_score", 0),
            "confidence": min(99, int(r.get("_score", 0) * 3)),
            "date": str(today),
            "raw_data": {
                "title": title,
                "text": text,
                "url": url,
                "source": source,
                "fetched_at": datetime.utcnow().isoformat(),
            },
        }).execute()
        saved += 1

    print(f"  💾 Saved {saved} signals to trend_signals")
    return saved


if __name__ == "__main__":
    import sys
    fetch_and_save_news(dry_run="--dry-run" in sys.argv)
