import requests
from datetime import datetime, timedelta
from pipeline.config import EXA_API_KEY, EXA_API_URL, EXA_NUM_RESULTS, EXA_DAYS_BACK


def search_trends(query: str, lang: str = "en") -> list[dict]:
    """
    Ищет тренды через Exa.ai neural search.
    lang="en" — глобальные тренды, lang="ru" — российский рынок.
    """
    date_from = (datetime.now() - timedelta(days=EXA_DAYS_BACK)).strftime("%Y-%m-%dT00:00:00Z")

    payload = {
        "query": query,
        "numResults": EXA_NUM_RESULTS,
        "startPublishedDate": date_from,
        "contents": {
            "text": {"maxCharacters": 2000}
        }
    }

    if lang == "ru":
        payload["includeDomains"] = [
            "vc.ru", "retail.ru", "foodretail.ru", "rb.ru",
            "habr.com", "rbc.ru", "kommersant.ru"
        ]

    response = requests.post(
        EXA_API_URL,
        json=payload,
        headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def format_results_for_prompt(results: list[dict]) -> str:
    """Форматирует результаты Exa.ai в текст для промпта Gemini."""
    if not results:
        return "Данные не найдены."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "—")
        url = r.get("url", "")
        text = r.get("text", "")[:500].replace('"', "'")
        lines.append(f"{i}. {title}\n   URL: {url}\n   {text}")
    return "\n\n".join(lines)
