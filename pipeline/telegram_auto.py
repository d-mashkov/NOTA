"""
Автоматический парсинг Telegram-каналов через Telethon.
Требует: TELEGRAM_API_ID, TELEGRAM_API_HASH из my.telegram.org
"""
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    from telethon.sync import TelegramClient
    from telethon import functions, types
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

from pipeline.config import TELEGRAM_API_ID, TELEGRAM_API_HASH

# Каналы для парсинга
FMCG_CHANNELS = [
    "fmcg_report",          # FMCG Report
    "retailru",             # Retail.ru
    "vcnews",               # vc.ru
    "produkty_pitaniya",    # Продукты питания
    "fmcg_russia",          # FMCG Russia
    "ecommercerus",         # E-commerce RU
]

SESSION_FILE = Path("data/telegram/.session")


def fetch_telegram_posts(
    channels: list[str] = None,
    days_back: int = 90,
    limit_per_channel: int = 100,
) -> list[dict]:
    """
    Автоматически скачивает посты из Telegram-каналов.
    Требует авторизации при первом запуске.
    """
    if not TELETHON_AVAILABLE:
        print("  ⚠️  Telethon не установлен: pip install telethon")
        return []

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("  ⚠️  TELEGRAM_API_ID / TELEGRAM_API_HASH не заданы в .env")
        return []

    channels = channels or FMCG_CHANNELS
    since = datetime.now() - timedelta(days=days_back)
    all_posts = []

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    with TelegramClient(str(SESSION_FILE), TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
        for channel in channels:
            try:
                entity = client.get_entity(channel)
                channel_name = getattr(entity, 'title', channel)
                print(f"    📱 {channel_name}: ", end="", flush=True)

                count = 0
                for msg in client.iter_messages(entity, limit=limit_per_channel, offset_date=None):
                    if msg.date.replace(tzinfo=None) < since:
                        break
                    if msg.text and len(msg.text) > 50:
                        all_posts.append({
                            "channel": channel_name,
                            "date": msg.date.strftime("%Y-%m-%d"),
                            "text": msg.text[:1000],
                            "views": getattr(msg, 'views', 0) or 0,
                            "url": f"https://t.me/{channel}/{msg.id}",
                        })
                        count += 1
                print(f"{count} постов")
            except Exception as e:
                print(f"    ⚠️  {channel}: {e}")

    return all_posts


def save_fetched_posts(posts: list[dict], filename: str = "auto_fetched.json") -> None:
    path = Path(f"data/telegram/{filename}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"name": "Auto-fetched", "messages": [
            {"id": i, "type": "message", "date": p["date"],
             "text": p["text"], "views": p["views"]}
            for i, p in enumerate(posts)
        ]}, f, ensure_ascii=False, indent=2)
    print(f"  💾 Сохранено {len(posts)} постов → {path}")
