from datetime import date


def build_prompt(
    category_name: str,
    category_name_en: str,
    exa_en_data: str,
    exa_ru_data: str,
    telegram_data: str,
    youtube_data: str = "",
    tiktok_data: str = "",
    linkedin_data: str = "",
) -> str:
    today = date.today().strftime("%Y-%m-%d")

    telegram_section = ""
    if telegram_data:
        telegram_section = f"\n\n### Telegram-каналы (FMCG-аналитика РФ):\n{telegram_data}"

    youtube_section = ""
    if youtube_data:
        youtube_section = f"\n\n### YouTube (видео-тренды, просмотры):\n{youtube_data}"

    tiktok_section = ""
    if tiktok_data:
        tiktok_section = f"\n\n### TikTok (вирусный контент):\n{tiktok_data}"

    linkedin_section = ""
    if linkedin_data:
        linkedin_section = f"\n\n### LinkedIn (B2B и профессиональные обсуждения):\n{linkedin_data}"

    return f"""Ты — аналитик FMCG-рынка России. На основе данных о трендах создай структурированный отчёт по продуктовой нише (NOTA).

Отвечай ТОЛЬКО валидным JSON без markdown-обёртки, без ```json, только чистый JSON.

Категория: {category_name} ({category_name_en})
Дата анализа: {today}

### Exa.ai — глобальные тренды (EN):
{exa_en_data}

### Exa.ai — тренды РФ:
{exa_ru_data}{telegram_section}{youtube_section}{tiktok_section}{linkedin_section}

На основе этих данных создай NOTA в JSON-формате:

{{
  "title": "Краткое название продуктовой ниши (до 60 символов)",
  "description": "2-3 предложения: что это, почему актуально для России",
  "trend_stage": "emerging | growing | hype | saturation",
  "competition_level": "low | medium | high",
  "recommendation": "launch | watch | skip",
  "report": {{
    "foreign_cases": "Примеры успешных продуктов в США/Европе/Китае. Конкретные бренды.",
    "demand_russia": "Анализ спроса в России: поисковые тренды, упоминания, интерес аудитории",
    "demand_global": "Глобальный тренд: страны-лидеры, динамика роста",
    "russian_market": "Анализ конкурентов в РФ: кто продаёт, цены, насколько развита ниша",
    "competitors": [{{"name": "Название бренда", "segment": "масс-маркет/премиум", "price_range": "150-300 руб"}}],
    "target_audience": "ЦА: возраст, образ жизни, боли, мотивация к покупке",
    "product_hypothesis": "Конкретная продуктовая гипотеза: что именно производить, в каком формате",
    "flavors_formats": "Рекомендуемые вкусы, объёмы упаковки, форматы",
    "market_size": "Оценка объёма рынка в рублях/штуках в год",
    "launch_difficulty": "low | medium | high. Объяснение.",
    "potential_margin": "Розничная цена, себестоимость, маржа %",
    "risks": "Основные риски: регуляторные, конкурентные, сезонные",
    "gtm": "Каналы выхода: Ozon, WB, ВкусВилл, фитнес-клубы. Приоритеты.",
    "ai_output": "Финальный вывод-резюме. 4-6 предложений. Конкретный, без воды.",
    "ai_recommendation": "Подробное обоснование рекомендации launch/watch/skip",
    "sources": [{{"title": "Название источника", "url": "", "type": "exa | news | telegram | marketplace"}}]
  }},
  "score_breakdown": {{
    "demand_russia_growth": 0,
    "foreign_confirmation": 0,
    "marketplace_sales": 0,
    "low_competition": 0,
    "launch_simplicity": 0,
    "potential_margin": 0,
    "media_buzz": 0,
    "fmcg_fit": 0,
    "total": 0
  }}
}}

Скоринг (total = сумма всех):
- demand_russia_growth: 0-20
- foreign_confirmation: 0-15
- marketplace_sales: 0-15
- low_competition: 0-15
- launch_simplicity: 0-10
- potential_margin: 0-10
- media_buzz: 0-10
- fmcg_fit: 0-5

Будь конкретным. Называй реальные бренды, цены, объёмы."""
