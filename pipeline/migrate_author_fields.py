"""
Миграция: добавляет колонки author_reviewed и author_rating в таблицу launch_ideas.
Запускается один раз: python3 -m pipeline.migrate_author_fields
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'), override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

SQL = """
ALTER TABLE launch_ideas
  ADD COLUMN IF NOT EXISTS author_reviewed BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS author_rating   SMALLINT DEFAULT NULL;
"""

def run():
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    # Supabase не открывает DDL через REST напрямую — используем management API
    # Альтернатива: pg-meta endpoint (доступен через Supabase Dashboard)
    # Пробуем через postgres-meta если есть, иначе выводим SQL для ручного запуска

    # Попытка через Supabase SQL API (доступна только в Pro)
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    # Пробуем через /rest/v1/rpc/exec (если такой RPC создан)
    # Иначе — выводим SQL для запуска в Supabase Dashboard → SQL Editor
    print("=" * 60)
    print("Для добавления колонок выполни этот SQL в Supabase Dashboard")
    print("(Dashboard → SQL Editor → New query):")
    print("=" * 60)
    print(SQL)
    print("=" * 60)
    print("Либо запусти через psql напрямую к базе.")

if __name__ == "__main__":
    run()
