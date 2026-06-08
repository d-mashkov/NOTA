"""
Launch Ideas Generator — генерирует идеи для запуска продуктов.
Каждый агент анализирует нишу и «защищает» идею со своей стороны.
Запускается по расписанию или вручную.
"""

import os
import sys
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'), override=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.agents.artem import search_social_trends
from pipeline.agents.petya import compare_trends_global_vs_russia
from pipeline.agents.vova import analyze_marketplace
from pipeline.agents.avoska import analyze_tg_channels
from pipeline.agents.polya import build_marketing_strategy
from pipeline.supabase_client import supabase

# Категории для генерации идей
IDEA_SEEDS = [
    {"title": "Протеиновые снеки нового поколения", "query": "protein snacks functional food"},
    {"title": "Функциональные напитки с адаптогенами", "query": "adaptogen drinks ashwagandha"},
    {"title": "Растительные альтернативы молоку", "query": "plant-based milk oat almond"},
    {"title": "Коллагеновые продукты красоты изнутри", "query": "collagen beauty supplements drinks"},
    {"title": "Снеки без сахара для детей", "query": "sugar-free kids snacks healthy"},
    {"title": "Пробиотические продукты для кишечника", "query": "probiotic gut health fermented"},
    {"title": "Спортивное питание для любителей", "query": "amateur sports nutrition fitness"},
    {"title": "Суперфуды в повседневной упаковке", "query": "superfoods spirulina chia everyday"},
]


def generate_idea(seed: dict):
    """Генерирует полную идею запуска через всех агентов."""
    title = seed["title"]
    query = seed["query"]
    print(f"\n{'='*50}")
    print(f"[Ideas] Генерирую идею: {title}")

    # Параллельно собираем данные от агентов
    print(f"[Ideas] → Артём ищет тренды...")
    artem = search_social_trends(query)

    print(f"[Ideas] → Петя анализирует SEO...")
    petya = compare_trends_global_vs_russia(query)

    print(f"[Ideas] → Вова смотрит маркетплейсы...")
    vova = analyze_marketplace(title)

    print(f"[Ideas] → Авоська читает каналы...")
    avoska = analyze_tg_channels(title)

    print(f"[Ideas] → Поля строит стратегию...")
    polya = build_marketing_strategy(title, context=f"{artem[:300]}\n{petya[:300]}\n{vova[:300]}")

    # Claude синтезирует общий вывод и скор
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    synthesis_prompt = f"""Ты — главный аналитик NOTA. На основе данных от команды агентов оцени идею запуска FMCG-продукта в России.

Идея: {title}

Данные агентов:
🔴 Артём (соцсети): {artem[:500]}
🟡 Петя (SEO): {petya[:500]}
🔵 Вова (маркетплейсы): {vova[:500]}
🛒 Авоська (FMCG-каналы): {avoska[:500]}
🟣 Поля (маркетинг): {polya[:500]}

Верни JSON (только JSON, без markdown):
{{
  "summary": "2-3 предложения — почему эта идея стоит внимания прямо сейчас",
  "score": 0-100,
  "category": "название категории (1-3 слова)",
  "artem_verdict": "1 предложение от Артёма — что говорят соцсети",
  "petya_verdict": "1 предложение от Пети — как обстоят дела с поиском в РФ",
  "vova_verdict": "1 предложение от Вовы — что на маркетплейсах",
  "avoska_verdict": "1 предложение от Авоськи — что говорит FMCG-тусовка",
  "polya_verdict": "1 предложение от Поли — как запускать"
}}"""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        raw = resp.content[0].text.strip()
        # Убираем markdown если есть
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
    except Exception as e:
        print(f"[Ideas] Ошибка синтеза: {e}")
        data = {
            "summary": "Перспективная ниша для запуска на российском рынке.",
            "score": 65,
            "category": "FMCG",
            "artem_verdict": artem[:100],
            "petya_verdict": petya[:100],
            "vova_verdict": vova[:100],
            "avoska_verdict": avoska[:100],
            "polya_verdict": polya[:100],
        }

    return {
        "title": title,
        "category": data.get("category", "FMCG"),
        "summary": data.get("summary", ""),
        "score": data.get("score", 65),
        "artem": f"🔴 {data.get('artem_verdict', '')}\n\n{artem[:600]}",
        "petya": f"🟡 {data.get('petya_verdict', '')}\n\n{petya[:600]}",
        "vova": f"🔵 {data.get('vova_verdict', '')}\n\n{vova[:600]}",
        "avoska": f"🛒 {data.get('avoska_verdict', '')}\n\n{avoska[:600]}",
        "polya": f"🟣 {data.get('polya_verdict', '')}\n\n{polya[:600]}",
        "status": "active",
    }


def run(limit: int = 5):
    """Генерирует N идей и сохраняет в Supabase."""
    import random

    # Удаляем старые идеи
    supabase.table("launch_ideas").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print(f"[Ideas] Старые идеи удалены")

    seeds = random.sample(IDEA_SEEDS, min(limit, len(IDEA_SEEDS)))

    for seed in seeds:
        idea = generate_idea(seed)
        if idea:
            supabase.table("launch_ideas").insert(idea).execute()
            print(f"[Ideas] ✅ Сохранена: {idea['title']} (score: {idea['score']})")

    print(f"\n[Ideas] Готово — сгенерировано {len(seeds)} идей")


if __name__ == "__main__":
    run(limit=5)
