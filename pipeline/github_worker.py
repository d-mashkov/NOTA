"""
GitHub Actions Worker — запускается в GitHub Actions (US runner, Anthropic OK).
Забирает ВСЕ pending-идеи из Supabase и обрабатывает их одну за одной.
"""

import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# В GitHub Actions переменные из ENV, не из .env файла
# Но если .env есть (локальный запуск) — загружаем
env_path = os.path.join(ROOT, '.env')
if os.path.exists(env_path):
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)

import anthropic
from pipeline.supabase_client import supabase
from pipeline.run_launch_ideas import generate_idea


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
            if s.get("verdict") and
               "ограничен" not in s.get("verdict", "") and
               "limited" not in s.get("verdict", "").lower()
        )
        return real_count >= 2
    except Exception:
        return False


def process_idea(idea_id: str, niche: str):
    print(f"\n🚀 Обрабатываю: '{niche}' (id={idea_id[:8]}...)")
    try:
        print("→ Строю seed через Claude Haiku...")
        seed = build_seed_via_claude(niche)
        print(f"→ seed: '{seed['title']}' | {seed['group']}")
        print(f"→ query: {seed['query'][:80]}...")

        result = generate_idea(seed)

        if not has_real_data(result):
            print("⚠️ Слабые данные от агентов — помечаю failed")
            supabase.table("launch_ideas").update({
                "status": "failed",
                "summary": "Агенты не нашли достаточно данных по этой нише. Попробуй уточнить запрос.",
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

        print(f"✅ Готово! score={result['score']}, title='{result['title']}'")

    except Exception as e:
        import traceback
        print(f"❌ Ошибка: {e}")
        traceback.print_exc()
        try:
            supabase.table("launch_ideas").update({
                "status": "failed",
                "summary": f"Ошибка анализа: {str(e)[:200]}",
            }).eq("id", idea_id).execute()
        except Exception:
            pass


def main():
    print("GitHub Actions Worker — ищу pending-идеи...")
    result = supabase.table("launch_ideas").select(
        "id,title"
    ).eq("status", "pending").order("created_at").execute()

    pending = result.data or []
    print(f"Найдено pending: {len(pending)}")

    if not pending:
        print("Нечего обрабатывать. Выход.")
        return

    for idea in pending:
        process_idea(idea["id"], idea["title"])

    print(f"\nВсего обработано: {len(pending)}")


if __name__ == "__main__":
    main()
