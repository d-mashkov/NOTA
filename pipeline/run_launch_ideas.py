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
from pipeline.structurer import structure_agent_output, compute_score

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
    # Постельное бельё и сон
    {"title": "Масс-премиум постельное бельё из эвкалиптового Lyocell", "query": "eucalyptus lyocell TENCEL bedding cooling sleep D2C Russia", "group": "Сон"},
    {"title": "D2C бренд постельного белья — конкурент ИКЕА в сегменте выше среднего", "query": "premium bedding D2C brand sleep recovery Russia market", "group": "Сон"},
]


def generate_idea(seed: dict):
    """Генерирует полную идею запуска через всех агентов."""
    title = seed["title"]
    query = seed["query"]
    group = seed.get("group", "FMCG")
    print(f"\n{'='*50}")
    print(f"[Ideas] Генерирую идею: {title}")

    print(f"[Ideas] → Артём ищет тренды...")
    artem_raw = search_social_trends(query)

    print(f"[Ideas] → Петя анализирует SEO...")
    petya_raw = compare_trends_global_vs_russia(query)

    print(f"[Ideas] → Вова смотрит маркетплейсы...")
    vova_raw = analyze_marketplace(title)

    print(f"[Ideas] → Авоська читает каналы...")
    avoska_raw = analyze_tg_channels(title)

    print(f"[Ideas] → Поля строит стратегию...")
    polya_raw = build_marketing_strategy(title, context=f"{artem_raw[:300]}\n{petya_raw[:300]}\n{vova_raw[:300]}")

    # Структурируем вывод каждого агента через Claude Haiku
    print(f"[Ideas] → Структурируем данные агентов...")
    structs = {
        "artem":  structure_agent_output("artem",  artem_raw,  title),
        "petya":  structure_agent_output("petya",  petya_raw,  title),
        "vova":   structure_agent_output("vova",   vova_raw,   title),
        "avoska": structure_agent_output("avoska", avoska_raw, title),
        "polya":  structure_agent_output("polya",  polya_raw,  title),
    }

    # Считаем балл по рубрике — не гадаем, а вычисляем
    computed_score, sub_scores = compute_score(structs)
    print(f"[Ideas] Субскоры: {sub_scores} → итог: {computed_score}")

    # Claude синтезирует общий вывод, скор и детальную аналитику
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    # Компактные вердикты из структур для синтез-промпта
    agent_verdicts = "\n".join([
        f"🔴 Артём (тренды, сила {structs['artem']['trend_strength']}/100): {structs['artem']['verdict']}",
        f"   Сигналы: {', '.join(structs['artem']['key_signals'][:3])}",
        f"🟡 Петя (спрос РФ {structs['petya']['search_demand_ru']}/100, {structs['petya']['trend_direction']}): {structs['petya']['verdict']}",
        f"   Запросы: {', '.join(structs['petya']['top_queries'][:3])}",
        f"🔵 Вова (активность {structs['vova']['market_activity']}/100, конкуренция: {structs['vova']['competition_density']}): {structs['vova']['verdict']}",
        f"   Цена: {structs['vova']['avg_price_range']}  Топ: {', '.join(structs['vova']['top_sellers'][:3]) or '—'}",
        f"🛒 Авоська (buzz {structs['avoska']['industry_buzz']}/100): {structs['avoska']['verdict']}",
        f"   Инсайты: {'; '.join(structs['avoska']['key_insights'][:2])}",
        f"🟣 Поля (GTM {structs['polya']['gtm_clarity']}/100): {structs['polya']['verdict']}",
        f"   Каналы: {', '.join(structs['polya']['top_channels'][:3])}  Срок: {structs['polya']['time_to_market']}",
    ])

    synthesis_prompt = f"""Ты — главный аналитик NOTA. Составь итоговую карточку идеи.

ВАЖНО: только про эту конкретную идею — не смешивай категории.
Балл уже рассчитан по рубрике ({computed_score}/100) — можешь скорректировать не более чем на ±8.

Идея: {title}
Группа: {group}
Рассчитанный балл: {computed_score}/100
Субскоры: спрос={sub_scores['demand']}, рынок={sub_scores['market']}, конкуренция={sub_scores['competition']}, тренд={sub_scores['trend']}, GTM={sub_scores['gtm']}

Вердикты агентов:
{agent_verdicts}

Дополнительные данные для market_size / growth_rate / key_players / entry_price:
{vova_raw[:600]}
{petya_raw[:400]}

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
  ],
  "roadmap": [
    {{
      "phase": "Фаза 1 — Подготовка",
      "months": "1–2 мес",
      "milestones": ["задача 1", "задача 2", "задача 3"]
    }},
    {{
      "phase": "Фаза 2 — Запуск",
      "months": "3–4 мес",
      "milestones": ["задача 1", "задача 2", "задача 3"]
    }},
    {{
      "phase": "Фаза 3 — Рост",
      "months": "5–8 мес",
      "milestones": ["задача 1", "задача 2", "задача 3"]
    }},
    {{
      "phase": "Фаза 4 — Масштаб",
      "months": "9–12 мес",
      "milestones": ["задача 1", "задача 2", "задача 3"]
    }}
  ],
  "value_chain": {{
    "selling_price": 890,
    "currency": "₽",
    "gross_margin_pct": 35,
    "unit_costs": {{
      "raw_materials": 120,
      "manufacturing": 80,
      "packaging": 45,
      "logistics": 60,
      "marketplace_fee_pct": 15,
      "marketing_pct": 10
    }},
    "scenarios": [
      {{"volume": 500,   "revenue": 445000,   "total_costs": 288750,   "gross_profit": 156250,   "margin_pct": 35}},
      {{"volume": 1000,  "revenue": 890000,   "total_costs": 578500,   "gross_profit": 311500,   "margin_pct": 35}},
      {{"volume": 5000,  "revenue": 4450000,  "total_costs": 2892500,  "gross_profit": 1557500,  "margin_pct": 35}},
      {{"volume": 10000, "revenue": 8900000,  "total_costs": 5785000,  "gross_profit": 3115000,  "margin_pct": 35}},
      {{"volume": 50000, "revenue": 44500000, "total_costs": 28925000, "gross_profit": 15575000, "margin_pct": 35}}
    ],
    "notes": "Расчёт без ФОТа. Основан на реальных данных рынка РФ для данной категории. При объёме от 5000 ед./мес. возможна экономия на сырье 5-10%."
  }}
}}"""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=6000,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        # Если JSON обрезан — пробуем починить добавив закрывающие скобки
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Пробуем найти последний валидный объект
            for end in range(len(raw), 0, -1):
                try:
                    data = json.loads(raw[:end] + '}}' if raw[:end].count('{') > raw[:end].count('}') else raw[:end] + '}')
                    break
                except Exception:
                    continue
            else:
                raise ValueError("JSON не восстановить")
    except Exception as e:
        print(f"[Ideas] Ошибка синтеза: {e}")
        data = {
            "summary": "Перспективная ниша для запуска на российском рынке.",
            "score": computed_score,
            "category": group,
            "artem_verdict": structs["artem"]["verdict"],
            "petya_verdict": structs["petya"]["verdict"],
            "vova_verdict": structs["vova"]["verdict"],
            "avoska_verdict": structs["avoska"]["verdict"],
            "polya_verdict": structs["polya"]["verdict"],
            "market_size": "",
            "growth_rate": "",
            "key_players": structs["vova"]["top_sellers"],
            "entry_price": structs["vova"]["avg_price_range"],
            "packaging_ideas": [],
            "launch_steps": [],
            "risks": [],
            "sources": [],
            "roadmap": [],
            "value_chain": {},
        }

    # detail_json — всё что нужно для страницы детали
    detail_json = {
        "market_size":     data.get("market_size", ""),
        "growth_rate":     data.get("growth_rate", ""),
        "key_players":     data.get("key_players", []),
        "entry_price":     data.get("entry_price", ""),
        "packaging_ideas": data.get("packaging_ideas", []),
        "launch_steps":    data.get("launch_steps", []),
        "risks":           data.get("risks", []),
        "sources":         data.get("sources", []),
        "roadmap":         data.get("roadmap", []),
        "value_chain":     data.get("value_chain", {}),
        "group":           group,
        # Субскоры рубрики — видны пользователю
        "sub_scores": sub_scores,
        # Структурированные данные агентов
        "structs": structs,
        # Полные тексты агентов
        "artem_full":  artem_raw,
        "petya_full":  petya_raw,
        "vova_full":   vova_raw,
        "avoska_full": avoska_raw,
        "polya_full":  polya_raw,
    }

    # Балл: computed_score из рубрики + корректировка Claude не более ±8
    claude_score = data.get("score", computed_score)
    final_score = max(computed_score - 8, min(computed_score + 8, int(claude_score)))

    return {
        "title":    title,
        "category": data.get("category", group),
        "summary":  data.get("summary", ""),
        "score":    final_score,
        "artem":  f"{structs['artem']['verdict']}\n\n{artem_raw[:800]}",
        "petya":  f"{structs['petya']['verdict']}\n\n{petya_raw[:800]}",
        "vova":   f"{structs['vova']['verdict']}\n\n{vova_raw[:800]}",
        "avoska": f"{structs['avoska']['verdict']}\n\n{avoska_raw[:800]}",
        "polya":  f"{structs['polya']['verdict']}\n\n{polya_raw[:800]}",
        "detail_json": json.dumps(detail_json, ensure_ascii=False),
        "status": "active",
    }


TARGET_TOTAL = 20  # сколько идей хотим держать в базе


def run(limit: int = None):
    """
    Накопительная генерация: не удаляет старые идеи.
    Добавляет новые до TARGET_TOTAL (или limit, если задан явно).
    Пропускает seed'ы, уже существующие в базе по title.
    """
    import random

    # Считаем и получаем уже существующие идеи
    existing = supabase.table("launch_ideas").select("title").eq("status", "active").execute()
    existing_titles = {row["title"].strip().lower() for row in (existing.data or [])}
    current_count = len(existing_titles)

    # Сколько нужно добавить
    target = TARGET_TOTAL if limit is None else limit
    to_generate = max(0, target - current_count)
    print(f"[Ideas] В базе: {current_count} идей. Нужно добавить: {to_generate}")

    if to_generate == 0:
        print(f"[Ideas] База уже заполнена ({current_count}/{target}). Ничего не делаем.")
        return

    # Фильтруем seeds — только те, которых ещё нет
    available = [s for s in IDEA_SEEDS if s["title"].strip().lower() not in existing_titles]
    if not available:
        print(f"[Ideas] Все seed'ы уже использованы. Перезапускаем с полным списком.")
        available = IDEA_SEEDS[:]

    seeds = random.sample(available, min(to_generate, len(available)))
    print(f"[Ideas] Будет сгенерировано: {len(seeds)} идей")

    generated = 0
    for seed in seeds:
        idea = generate_idea(seed)
        if idea:
            supabase.table("launch_ideas").insert(idea).execute()
            print(f"[Ideas] ✅ Сохранена: {idea['title']} (score: {idea['score']})")
            generated += 1

    print(f"\n[Ideas] Готово — добавлено {generated} идей. Итого в базе: {current_count + generated}")


if __name__ == "__main__":
    run()  # добирает до TARGET_TOTAL (20)
