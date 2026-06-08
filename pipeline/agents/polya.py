"""
Агент Поля — маркетолог FMCG.
На основе маркетинговых скиллов: positioning, GTM, launch strategy, copywriting.
Упаковывает найденные тренды и ниши под российский рынок.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'), override=True)


def _grok_request(prompt: str) -> str:
    """Запрос к Grok с web_search."""
    key = os.getenv("GROK_API_KEY", "")
    if not key:
        return ""
    try:
        r = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "grok-4.3",
                "tools": [{"type": "web_search"}],
                "input": [{"role": "user", "content": prompt}],
            },
            timeout=40,
        )
        r.raise_for_status()
        data = r.json()
        parts = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        parts.append(block.get("text", ""))
        return "\n".join(parts).strip()
    except Exception as e:
        print(f"[Поля] Grok error: {e}")
        return ""


def build_marketing_strategy(query: str, context: str = "") -> str:
    """
    Разрабатывает маркетинговую стратегию для продукта/ниши под РФ рынок.
    Использует фреймворки: позиционирование April Dunford, ICP, GTM, launch strategy.
    """
    print(f"[Поля] Маркетинг-стратегия: {query}")

    prompt = f"""Ты — опытный FMCG-маркетолог с экспертизой в российском рынке.
Разработай маркетинговую стратегию для запуска продукта/ниши: {query}

{"Дополнительный контекст: " + context if context else ""}

Используй фреймворки:
1. Позиционирование по April Dunford (альтернативы, уникальная ценность, покупатель)
2. ICP (идеальный покупатель для России)
3. GTM — каналы для РФ (WB/Ozon, розница, соцсети, ТГ)
4. Ключевые сообщения и УТП

Ответь на русском, структурировано. Максимум 400 слов.
Используй ТОЛЬКО *жирный* через одинарные звёздочки, эмодзи для разделов, обычный текст.
НЕ используй ##, ###, ---, ** двойные звёздочки."""

    result = _grok_request(prompt)
    if not result:
        # Fallback — Claude сгенерирует без web search
        return _generate_strategy_local(query)

    return result + "\n\n🟣 *Поля* (маркетолог · позиционирование & GTM)"


def _generate_strategy_local(query: str) -> str:
    """Локальная генерация стратегии без внешних API."""
    return f"""🟣 *Поля анализирует: {query}*

🎯 *Позиционирование (April Dunford):*
• Альтернативы: обычные снеки, DIY рецепты, импортные аналоги
• Уникальная ценность: [нужен анализ конкурентов]
• Покупатель: ЗОЖ-аудитория 25-45 лет, Москва + города 1М+

👤 *ICP для России:*
• Женщины/мужчины 25-40, доход средний+
• Ценят состав, натуральность, удобство
• Покупают на WB/Ozon или в специализированных магазинах

📦 *GTM — каналы запуска:*
• WB/Ozon — основной канал (60-70% FMCG e-com)
• Telegram-каналы ЗОЖ (охват без рекламы)
• Instagram/ВКонтакте — инфлюенсеры нутрициологи
• Офлайн: сети ВкусВилл, Магнит, Лента

💬 *Ключевые сообщения:*
• [Требует анализа трендов от Артёма и Пети]

🟣 *Поля* (маркетолог · позиционирование & GTM)"""


def create_product_concept(
    product_idea: str,
    trend_data: str = "",
    market_data: str = ""
) -> str:
    """
    Создаёт готовую концепцию продукта для запуска:
    - Название и УТП
    - Упаковка идеи
    - Ценовое позиционирование
    - Запускной план
    """
    print(f"[Поля] Концепция продукта: {product_idea}")

    context_parts = []
    if trend_data:
        context_parts.append(f"Тренды: {trend_data[:500]}")
    if market_data:
        context_parts.append(f"Рынок: {market_data[:500]}")
    context = "\n".join(context_parts)

    prompt = f"""Ты — FMCG-маркетолог, специалист по запускам в России.
Создай концепцию продукта для запуска: {product_idea}

{context}

Разработай:
1. 3 варианта названия (русское + транслитерация)
2. УТП в одной фразе (под WB/Ozon карточку)
3. Ценовая полка (сравни с конкурентами)
4. Ключевые изображения/визуал упаковки
5. Топ-3 ошибки при запуске этой категории в РФ
6. Launch checklist — первые 30 дней

Ответь на русском. Максимум 350 слов.
Только *жирный* через одинарные звёздочки и эмодзи. Без ## ### ---."""

    result = _grok_request(prompt)
    if result:
        return result + "\n\n🟣 *Поля* (маркетолог · концепция продукта)"

    return f"🟣 Поля: не удалось сгенерировать концепцию для '{product_idea}'. Попробуй уточнить запрос."


def analyze_competition_rf(category: str) -> str:
    """
    Конкурентный анализ категории на РФ рынке.
    Кто топ-игроки, как позиционируются, где слабые места.
    """
    print(f"[Поля] Конкурентный анализ: {category}")

    prompt = f"""Ты — FMCG-маркетолог, анализируешь конкурентную среду в России.
Сделай конкурентный анализ категории: {category}

Найди и покажи:
• Топ-5 брендов в категории на российском рынке (WB, Ozon, ритейл)
• Ценовые сегменты (эконом / средний / премиум)
• Как каждый позиционируется (УТП, ключевые сообщения)
• Слабые места конкурентов — где можно зайти
• Рекомендация: какую нишу занять новому игроку

Ответь на русском. Максимум 350 слов.
Только *жирный* одинарными звёздочками и эмодзи. Без ## ### ---."""

    result = _grok_request(prompt)
    if result:
        return result + "\n\n🟣 *Поля* (маркетолог · конкурентный анализ)"

    return f"🟣 Поля: нет данных по конкурентам в '{category}'"


def package_insights_for_launch(
    trend_summary: str,
    category: str
) -> str:
    """
    Упаковывает все данные от других агентов в готовый launch brief.
    Принимает на вход сводку от Артёма/Пети/Вовы/Авоськи.
    """
    print(f"[Поля] Launch brief: {category}")

    prompt = f"""Ты — директор по маркетингу FMCG-стартапа в России.
На основе аналитики создай launch brief для категории: {category}

Аналитика от команды:
{trend_summary[:1500]}

Создай launch brief:
🎯 *Гипотеза продукта* — что запускаем и почему сейчас
👤 *Целевая аудитория* — 2-3 конкретных портрета
💡 *Позиционирование* — УТП в 1 предложении
📦 *Каналы запуска* — приоритеты для РФ
📅 *План на 30 дней* — milestone по неделям
⚠️ *Риски* — топ-3 чего избегать

Ответь на русском. Максимум 450 слов.
Только *жирный* одинарными звёздочками и эмодзи. Без ## ### ---."""

    result = _grok_request(prompt)
    if result:
        return result + "\n\n🟣 *Поля* (маркетолог · launch brief)"

    return f"🟣 Поля: не удалось создать launch brief для '{category}'"
