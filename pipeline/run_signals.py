"""
Собирает свежие сигналы из LinkedIn и Reddit по FMCG-темам через Exa.
Сохраняет в Supabase trend_signals. Запускать раз в неделю.
"""

import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'), override=True)

from exa_py import Exa
from pipeline.supabase_client import supabase

exa = Exa(api_key=os.getenv("EXA_API_KEY", ""))

# Темы для поиска
FMCG_QUERIES = [
    "FMCG Russia consumer trends 2025 2026",
    "protein snacks functional food trends",
    "plant based drinks market Russia",
    "healthy snacks market growth Russia",
    "FMCG новинки продукты Россия тренд",
]

REDDIT_COMMUNITIES = [
    "site:reddit.com/r/food",
    "site:reddit.com/r/nutrition",
    "site:reddit.com/r/veganfitness",
    "site:reddit.com/r/supplements",
    "site:reddit.com/r/AskCulinary",
]


def _exa_search(query: str, domain_filter: str = "", num: int = 5) -> list:
    try:
        q = f"{domain_filter} {query}".strip() if domain_filter else query
        result = exa.search_and_contents(
            q,
            num_results=num,
            text={"max_characters": 500},
            start_published_date=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%dT00:00:00Z"),
        )
        return result.results or []
    except Exception as e:
        print(f"  [Exa] ошибка: {e}")
        return []


def collect_linkedin() -> list[dict]:
    """Собирает LinkedIn сигналы."""
    rows = []
    today = date.today().isoformat()

    for query in FMCG_QUERIES[:3]:
        results = _exa_search(f"site:linkedin.com {query}", num=4)
        for r in results:
            title = (r.title or r.url or '')[:200]
            text = (r.text or '')[:600]
            if len(text) < 50:
                continue
            pub_date = r.published_date[:10] if r.published_date else today
            rows.append({
                'keyword': title[:200],
                'source': 'linkedin',
                'date': pub_date,
                'raw_data': {
                    'title': title,
                    'text': text,
                    'url': r.url or '',
                },
                'value': 50,
            })
        print(f"  LinkedIn '{query[:40]}': {len(results)} результатов")

    return rows


def collect_reddit() -> list[dict]:
    """Собирает Reddit обсуждения по FMCG темам."""
    rows = []
    today = date.today().isoformat()

    # Reddit/Food-медиа: ищем потребительские обсуждения и обзоры продуктов
    reddit_queries = [
        "FMCG functional food new product launch 2025 2026 consumer trend",
        "protein snacks healthy food new products reviews market 2025",
        "plant based food beverage trend market growth 2025",
        "functional drinks energy gut health consumer trend 2025",
        "healthy snacks market new launches consumer reviews 2025",
    ]
    for query in reddit_queries:
        results = _exa_search(query, num=4)
        # Фильтруем: берём только если URL похож на обсуждение/обзор
        results = [r for r in results if r.url and not 'linkedin.com' in r.url]
        for r in results:
            title = (r.title or r.url or '')[:200]
            text = (r.text or '')[:600]
            if len(text) < 50:
                continue
            pub_date = r.published_date[:10] if r.published_date else today
            rows.append({
                'keyword': title[:200],
                'source': 'reddit',
                'date': pub_date,
                'raw_data': {
                    'title': title,
                    'text': text,
                    'url': r.url or '',
                },
                'value': 50,
            })
        print(f"  Reddit '{query[:40]}': {len(results)} результатов")

    return rows


def save_rows(rows: list[dict], source: str) -> None:
    if not rows:
        print(f"  Нет данных для {source}")
        return

    # Удаляем дубли по keyword (уже существующие в БД за последние 3 месяца)
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    existing = supabase.table('trend_signals').select('keyword').eq('source', source).gte('date', cutoff).execute()
    existing_keywords = {r['keyword'] for r in (existing.data or [])}

    new_rows = [r for r in rows if r['keyword'] not in existing_keywords]
    print(f"  {source}: {len(rows)} найдено, {len(new_rows)} новых (пропущено {len(rows)-len(new_rows)} дублей)")

    if not new_rows:
        return

    res = supabase.table('trend_signals').insert(new_rows).execute()
    print(f"  ✅ Сохранено {len(res.data)} записей")


def run():
    print("[Сигналы] Сбор LinkedIn + Reddit...")

    print("\n📌 LinkedIn:")
    linkedin_rows = collect_linkedin()
    save_rows(linkedin_rows, 'linkedin')

    print("\n🟠 Reddit:")
    reddit_rows = collect_reddit()
    save_rows(reddit_rows, 'reddit')

    print("\n✅ Готово!")


if __name__ == '__main__':
    run()
