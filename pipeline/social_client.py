"""
Парсинг TikTok и LinkedIn через Exa.ai с фильтрацией по домену.
"""
import requests
from pipeline.config import EXA_API_KEY, EXA_API_URL


def _exa_search(query: str, domain: str, num_results: int = 8) -> list[dict]:
    resp = requests.post(EXA_API_URL, json={
        "query": query,
        "numResults": num_results,
        "includeDomains": [domain],
        "contents": {"text": {"maxCharacters": 400}},
        "type": "neural",
    }, headers={"x-api-key": EXA_API_KEY}, timeout=20)

    if resp.status_code != 200:
        return []
    return resp.json().get("results", [])


def search_tiktok(query: str) -> list[dict]:
    """Ищет упоминания темы в TikTok через Exa."""
    return _exa_search(f"{query} tiktok trend viral", "tiktok.com")


def search_linkedin(query: str) -> list[dict]:
    """Ищет профессиональные обсуждения темы на LinkedIn."""
    return _exa_search(f"{query} FMCG market trend", "linkedin.com", num_results=6)


def format_social_for_prompt(tiktok: list[dict], linkedin: list[dict]) -> str:
    """Форматирует TikTok + LinkedIn данные для промпта."""
    lines = []

    if tiktok:
        lines.append("=== TikTok ===")
        for r in tiktok[:5]:
            lines.append(
                f"[TikTok] {r.get('title', '')}\n"
                f"{r.get('text', '')[:250]}\n"
                f"URL: {r.get('url', '')}"
            )

    if linkedin:
        lines.append("\n=== LinkedIn ===")
        for r in linkedin[:4]:
            lines.append(
                f"[LinkedIn] {r.get('title', '')}\n"
                f"{r.get('text', '')[:250]}\n"
                f"URL: {r.get('url', '')}"
            )

    return "\n\n".join(lines)
