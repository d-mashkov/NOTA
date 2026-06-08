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

# Категории для генерации идей — разнообразные ниши
IDEA_SEEDS = [
    # Здоровое питание
    {"title": "Протеиновые снеки нового поколения", "query": "protein snacks functional food", "group": "Питание"},
    {"title": "Функциональные напитки с адаптогенами", "query": "adaptogen drinks ashwagandha", "group": "Питание"},
    {"title": "Растительные альтернативы молоку", "query": "plant-based milk oat almond", "group": "Питание"},
    {"title": "Коллагеновые продукты красоты изнутри", "query": "collagen beauty supplements drinks", "group": "Питание"},
    {"title": "Снеки без сахара для детей", "query": "sugar-free kids snacks healthy", "group": "Питание"},
    {"title": "Пробиотические продукты для кишечника", "query": "probiotic gut health fermented", "group": "Питание"},
    {"title": "Спортивное питание для любителей", "query": "amateur sports nutrition fitness", "group": "Питание"},
    {"title": "Суперфуды в повседневной упаковке", "query": "superfoods spirulina chia everyday", "group": "Питание"},
    # Уход и красота
    {"title": "Электрические зубные щётки нового поколения", "query": "electric toothbrush sonic smart 2025", "group": "Уход"},
    {"title": "Зубные пасты с угольным детоксом", "query": "charcoal whitening toothpaste natural", "group": "Уход"},
    {"title": "Патчи для кожи — моментальный уход", "query": "hydrogel patches skincare spot treatment", "group": "Уход"},
    {"title": "Натуральные дезодоранты без алюминия", "query": "natural deodorant aluminum-free biome", "group": "Уход"},
    {"title": "Шампуни против выпадения волос", "query": "hair loss shampoo biotin scalp treatment 2025", "group": "Уход"},
    # Гаджеты и технологии
    {"title": "Фитнес-трекеры для массового рынка", "query": "fitness tracker wearable affordable 2025", "group": "Гаджеты"},
    {"title": "Умные бутылки для воды", "query": "smart water bottle hydration tracker", "group": "Гаджеты"},
    {"title": "Портативные массажёры и релакс-гаджеты", "query": "portable massager percussion recovery device", "group": "Гаджеты"},
    {"title": "Беспроводные наушники среднего сегмента", "query": "wireless earbuds mid-range TWS 2025", "group": "Гаджеты"},
    # Никотин
    {"title": "Никотиновые паучи — бестабачный нагрев", "query": "nicotine pouches snus tobacco-free 2025", "group": "Никотин"},
    {"title": "POD-системы нового поколения", "query": "pod vape system nicotine device 2025", "group": "Никотин"},
    {"title": "Жевательный табак и снюс в РФ", "query": "snus chewing tobacco Russia market 2025", "group": "Никотин"},
    {"title": "ОЭСДН — одноразовые электронные сигареты", "query": "disposable vape OESDN Russia market trend", "group": "Никотин"},
    # Дом и быт
    {"title": "Экологичные средства для уборки", "query": "eco cleaning products concentrate refill", "group": "Дом"},
    {"title": "Капсульный стиральный порошок", "query": "laundry pods capsules detergent market 2025", "group": "Дом"},
    {"title": "Умные освежители воздуха", "query": "smart air freshener diffuser auto home fragrance", "group": "Дом"},
]


def generate_idea(seed: dict):
    """Генерирует полную идею запуска через всех агентов."""
    title = seed["title"]
    query = seed["query"]
    group = seed.get("group", "FMCG")
    print(f"\n{'='*50}")
    print(f"[Ideas] Генерирую идею: {title}")

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

    # Claude синтезирует общий вывод, скор и детальную аналитику
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    synthesis_prompt = f"""Ты — главный аналитик NOTA. Оцени идею запуска продукта в России на основе данных от агентов.

Идея: {title}
Группа: {group}

Данные агентов:
🔴 Артём (соцсети/тренды): {artem[:700]}
🟡 Петя (SEO/поиск): {petya[:700]}
🔵 Вова (маркетплейсы WB/Ozon): {vova[:700]}
🛒 Авоська (FMCG Telegram-каналы): {avoska[:700]}
🟣 Поля (маркетинг/GTM): {polya[:700]}

Верни JSON (только JSON, без markdown):
{{
  "summary": "2-3 предложения — почему эта идея стоит внимания прямо сейчас",
  "score": 0-100,
  "category": "название категории (1-3 слова)",
  "artem_verdict": "1 предложение от Артёма",
  "petya_verdict": "1 предложение от Пети",
  "vova_verdict": "1 предложение от Вовы",
  "avoska_verdict": "1 предложение от Авоськи",
  "polya_verdict": "1 предложение от Поли",
  "market_size": "оценка объёма рынка в РФ (цифра + источник если есть)",
  "growth_rate": "темп роста категории в % или описание",
  "key_players": ["топ 3-5 игроков на рынке РФ"],
  "entry_price": "рекомендуемая цена входа на полку (диапазон)",
  "packaging_ideas": [
    "идея упаковки 1 с описанием",
    "идея упаковки 2 с описанием",
    "идея упаковки 3 с описанием"
  ],
  "launch_steps": [
    "шаг 1 запуска",
    "шаг 2 запуска",
    "шаг 3 запуска",
    "шаг 4 запуска"
  ],
  "risks": ["риск 1", "риск 2", "риск 3"],
  "sources": [
    {{"title": "название источника/статьи", "url": "https://...", "note": "что оттуда взяли"}},
    {{"title": "название источника/статьи", "url": "https://...", "note": "что оттуда взяли"}}
  ]
}}"""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        raw = resp.content[0].text.strip()
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
            "category": group,
            "artem_verdict": artem[:100],
            "petya_verdict": petya[:100],
            "vova_verdict": vova[:100],
            "avoska_verdict": avoska[:100],
            "polya_verdict": polya[:100],
            "market_size": "",
            "growth_rate": "",
            "key_players": [],
            "entry_price": "",
            "packaging_ideas": [],
            "launch_steps": [],
            "risks": [],
            "sources": [],
        }

    # detail_json — всё что нужно для страницы детей
    detail_json = {
        "market_size": data.get("market_size", ""),
        "growth_rate": data.get("growth_rate", ""),
        "key_players": data.get("key_players", []),
        "entry_price": data.get("entry_price", ""),
        "packaging_ideas": data.get("packaging_ideas", []),
        "launch_steps": data.get("launch_steps", []),
        "risks": data.get("risks", []),
        "sources": data.get("sources", []),
        "group": group,
        # Полные тексты агентов (не обрезанные)
        "artem_full": artem,
        "petya_full": petya,
        "vova_full": vova,
        "avoska_full": avoska,
        "polya_full": polya,
    }

    return {
        "title": title,
        "category": data.get("category", group),
        "summary": data.get("summary", ""),
        "score": data.get("score", 65),
        "artem": f"🔴 {data.get('artem_verdict', '')}\n\n{artem[:800]}",
        "petya": f"🟡 {data.get('petya_verdict', '')}\n\n{petya[:800]}",
        "vova": f"🔵 {data.get('vova_verdict', '')}\n\n{vova[:800]}",
        "avoska": f"🛒 {data.get('avoska_verdict', '')}\n\n{avoska[:800]}",
        "polya": f"🟣 {data.get('polya_verdict', '')}\n\n{polya[:800]}",
        "detail_json": json.dumps(detail_json, ensure_ascii=False),
        "status": "active",
    }


def run(limit: int = 5):
    """Генерирует N идей и сохраняет в Supabase."""
    import random

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
