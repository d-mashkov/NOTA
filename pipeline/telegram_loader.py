import json
from pathlib import Path

TELEGRAM_DATA_DIR = Path(__file__).parent.parent / "data" / "telegram"


def load_telegram_posts(filepath: str) -> list[dict]:
    """
    Загружает посты из Telegram JSON-экспорта.
    Фильтрует служебные сообщения и пустые тексты.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    channel_name = data.get("name", "Unknown")
    posts = []

    for msg in data.get("messages", []):
        if msg.get("type") != "message":
            continue
        text = msg.get("text", "")
        if isinstance(text, list):
            text = " ".join(
                part if isinstance(part, str) else part.get("text", "")
                for part in text
            )
        if not text.strip():
            continue
        posts.append({
            "channel": channel_name,
            "date": msg.get("date", "")[:10],
            "text": text.strip(),
            "views": msg.get("views", 0),
            "forwards": msg.get("forwards", 0),
        })

    return posts


def load_all_telegram_posts() -> list[dict]:
    """Загружает все JSON-файлы из data/telegram/."""
    all_posts = []
    if not TELEGRAM_DATA_DIR.exists():
        return []
    for file in TELEGRAM_DATA_DIR.glob("*.json"):
        all_posts.extend(load_telegram_posts(str(file)))
    return all_posts


def search_relevant_posts(posts: list[dict], keywords: list[str]) -> list[dict]:
    """
    Ищет посты, содержащие хотя бы одно из ключевых слов.
    Возвращает отсортированные по views.
    """
    keywords_lower = [kw.lower() for kw in keywords]
    relevant = [
        p for p in posts
        if any(kw in p["text"].lower() for kw in keywords_lower)
    ]
    return sorted(relevant, key=lambda p: p.get("views", 0), reverse=True)


def format_telegram_for_prompt(posts: list[dict], max_posts: int = 5) -> str:
    """Форматирует Telegram-посты в текст для промпта."""
    if not posts:
        return ""
    lines = []
    for p in posts[:max_posts]:
        lines.append(f"[{p['channel']} | {p['date']} | 👁 {p.get('views', 0)}]\n{p['text']}")
    return "\n\n".join(lines)
