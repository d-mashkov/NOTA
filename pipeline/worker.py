"""
Worker — запускается в фоне API для обработки пользовательского запроса.
Использование: python worker.py <idea_id> <niche_text>
"""

import os
import sys
import json

# Путь к корню проекта
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'), override=True)

import anthropic
from pipeline.supabase_client import supabase
from pipeline.run_launch_ideas import generate_idea


def build_seed_via_claude(niche: str) -> dict:
    """
    Использует Claude Haiku чтобы построить хороший seed для пайплайна.
    Возвращает {"title", "query", "group"}.
    """
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
- "electric toothbrush sonic smart mid-range Russia retail market 2025"
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
    """Проверяет что агенты вернули реальные данные, а не заглушки."""
    try:
        detail = json.loads(result.get("detail_json", "{}"))
        structs = detail.get("structs", {})

        # Считаем сколько агентов дали реальные данные (не "Данные ограничены")
        real_count = 0
        for agent_name, s in structs.items():
            verdict = s.get("verdict", "")
            if verdict and "ограничен" not in verdict and "limited" not in verdict.lower():
                real_count += 1

        return real_count >= 2  # хотя бы 2 агента вернули что-то реальное
    except Exception:
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: worker.py <idea_id> <niche_text>")
        sys.exit(1)

    idea_id = sys.argv[1]
    niche = " ".join(sys.argv[2:])

    print(f"[Worker] Запускаю анализ ниши: '{niche}' (id={idea_id})")

    try:
        # Шаг 1: Claude Haiku строит умный seed
        print(f"[Worker] → Haiku строит seed...")
        seed = build_seed_via_claude(niche)
        print(f"[Worker] seed: title='{seed['title']}' group='{seed['group']}' query='{seed['query'][:60]}...'")

        # Шаг 2: Запускаем полный пайплайн
        result = generate_idea(seed)

        # Шаг 3: Проверяем качество данных
        if not has_real_data(result):
            print(f"[Worker] ⚠️ Агенты вернули слабые данные, помечаем как failed")
            supabase.table("launch_ideas").update({
                "status": "failed",
                "summary": "Агенты не нашли достаточно данных по этой нише. Попробуй уточнить запрос.",
            }).eq("id", idea_id).execute()
            return

        # Шаг 4: Обновляем запись — меняем статус на active
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

        print(f"[Worker] ✅ Готово! score={result['score']}")

    except Exception as e:
        import traceback
        print(f"[Worker] ❌ Ошибка: {e}")
        traceback.print_exc()
        try:
            supabase.table("launch_ideas").update({
                "status": "failed",
                "summary": f"Ошибка анализа: {str(e)[:200]}",
            }).eq("id", idea_id).execute()
        except Exception:
            pass


if __name__ == "__main__":
    main()
