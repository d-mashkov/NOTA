"""
Mac Worker Poller — запускается на Mac, опрашивает Supabase на pending-идеи
и запускает pipeline локально (Mac имеет доступ к Anthropic API).

Запуск:
  cd /Users/denismaskov/Nota
  python pipeline/mac_worker_poller.py

Или в фоне:
  nohup python pipeline/mac_worker_poller.py >> /tmp/nota-poller.log 2>&1 &
"""

import os
import sys
import json
import time
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'), override=True)

from pipeline.supabase_client import supabase
from pipeline.run_launch_ideas import generate_idea
import anthropic


POLL_INTERVAL = 30  # секунд между проверками


def build_seed_via_claude(niche: str) -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": f"""Ты помогаешь анализировать ниши для запуска FMCG/D2C продуктов на российском рынке.

Пользователь хочет проанализировать нишу: «{niche}»

Верни JSON (только JSON, без markdown):
{{
  "title": "Красивое название идеи для запуска (3-6 слов, по-русски)",
  "query": "Поисковый запрос на английском для агентов (15-25 слов) — конкретная категория продукта, ключевые слова рынка, Russia, 2025, бренд/D2C/retail",
  "group": "одно из: Питание | Уход | Гаджеты | Никотин | Дом | Сон | FMCG"
}}

Примеры хороших query:
- "cottage cheese snacks healthy protein Russia FMCG market 2025 retail D2C brand"
- "natural deodorant aluminum-free biome skincare Russia D2C market 2025"
"""
        }]
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())
    return {
        "title": data.get("title", niche),
        "query": data.get("query", f"{niche} Russia market 2025 brand"),
        "group": data.get("group", "FMCG"),
    }


def has_real_data(result: dict) -> bool:
    try:
        detail = json.loads(result.get("detail_json", "{}"))
        structs = detail.get("structs", {})
        real_count = sum(
            1 for s in structs.values()
            if s.get("verdict") and "ограничен" not in s.get("verdict", "") and "limited" not in s.get("verdict", "").lower()
        )
        return real_count >= 2
    except Exception:
        return False


def process_idea(idea_id: str, niche: str):
    print(f"\n[Poller] 🚀 Обрабатываю: '{niche}' (id={idea_id[:8]}...)")
    try:
        print(f"[Poller] → Строю seed через Claude Haiku...")
        seed = build_seed_via_claude(niche)
        print(f"[Poller] seed: '{seed['title']}' | {seed['group']} | query: {seed['query'][:50]}...")

        result = generate_idea(seed)

        if not has_real_data(result):
            print(f"[Poller] ⚠️ Слабые данные — помечаю failed")
            supabase.table("launch_ideas").update({
                "status": "failed",
                "summary": "Агенты не нашли достаточно данных. Попробуй уточнить нишу.",
            }).eq("id", idea_id).execute()
            return

        supabase.table("launch_ideas").update({
            "status": "active",
            "title": result["title"],
            "category": result["category"],
            "summary": result["summary"],
            "score": result["score"],
            "artem": result.get("artem", ""),
            "petya": result.get("petya", ""),
            "vova": result.get("vova", ""),
            "avoska": result.get("avoska", ""),
            "polya": result.get("polya", ""),
            "detail_json": result["detail_json"],
        }).eq("id", idea_id).execute()

        print(f"[Poller] ✅ Готово! score={result['score']}, title='{result['title']}'")

    except Exception as e:
        import traceback
        print(f"[Poller] ❌ Ошибка: {e}")
        traceback.print_exc()
        try:
            supabase.table("launch_ideas").update({
                "status": "failed",
                "summary": f"Ошибка анализа: {str(e)[:200]}",
            }).eq("id", idea_id).execute()
        except Exception:
            pass


def main():
    print(f"[Poller] 🟢 Запущен. Опрашиваю Supabase каждые {POLL_INTERVAL} сек...")
    print(f"[Poller] Ctrl+C для остановки\n")

    while True:
        try:
            # Ищем pending-идеи
            result = supabase.table("launch_ideas").select(
                "id,title"
            ).eq("status", "pending").order("created_at").execute()

            pending = result.data or []

            if pending:
                print(f"[Poller] Найдено {len(pending)} pending-идей")
                for idea in pending:
                    process_idea(idea["id"], idea["title"])
            else:
                print(f"[Poller] Нет pending-идей. Жду {POLL_INTERVAL} сек...", end="\r")

        except KeyboardInterrupt:
            print("\n[Poller] Остановлен.")
            break
        except Exception as e:
            print(f"[Poller] Ошибка polling: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
