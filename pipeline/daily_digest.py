"""
Daily Digest — ежедневный отчёт администратору в Telegram.
Запускается раз в день через Railway Cron.
Отправляет статистику бота: пользователи, запросы, активность.
"""

import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'), override=True)

from pipeline.supabase_client import supabase

ADMIN_CHAT_ID = 1567547246  # Denis Mashkov
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def send_telegram(chat_id: int, text: str):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )


def run_digest():
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    yesterday = (now - timedelta(days=1)).date().isoformat()
    week_ago = (now - timedelta(days=7)).date().isoformat()

    # Все пользователи
    users = supabase.table("telegram_users").select("*").execute().data or []
    total_users = len(users)
    new_today = sum(1 for u in users if u.get("first_seen", "")[:10] == today)
    new_week = sum(1 for u in users if u.get("first_seen", "")[:10] >= week_ago)
    active_today = sum(1 for u in users if u.get("last_seen", "")[:10] == today)
    total_messages = sum(u.get("message_count", 0) for u in users)

    # Запросы за сегодня
    msgs_today = supabase.table("chat_messages") \
        .select("*").eq("role", "user") \
        .gte("created_at", today) \
        .order("created_at", desc=True).limit(5).execute().data or []

    # Формируем сообщение
    lines = [
        f"📊 *Дайджест NOTA Bot* — {now.strftime('%d.%m.%Y')}",
        "",
        f"👥 *Пользователи:* {total_users} всего",
        f"  • Новых сегодня: {new_today}",
        f"  • Новых за неделю: {new_week}",
        f"  • Активны сегодня: {active_today}",
        f"  • Всего сообщений: {total_messages}",
        "",
    ]

    if msgs_today:
        lines.append("💬 *Запросы сегодня:*")
        user_map = {u["chat_id"]: u for u in users}
        for m in msgs_today[:5]:
            u = user_map.get(m["chat_id"], {})
            name = u.get("username") or u.get("first_name") or "?"
            lines.append(f"  @{name}: _{m['message'][:80]}_")
        lines.append("")

    # Топ пользователей
    top = sorted(users, key=lambda u: u.get("message_count", 0), reverse=True)[:3]
    if top:
        lines.append("🏆 *Топ пользователи:*")
        for i, u in enumerate(top, 1):
            name = u.get("username") or u.get("first_name") or "?"
            lines.append(f"  {i}. @{name} — {u['message_count']} сообщений")

    send_telegram(ADMIN_CHAT_ID, "\n".join(lines))
    print(f"[Digest] Отправлен дайджест за {today}")


if __name__ == "__main__":
    run_digest()
