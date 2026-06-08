"""
Агент Чукча — оркестратор на Claude claude-sonnet с tool_use.
Принимает вопрос, решает каких агентов вызвать, синтезирует ответ.
"""

import os
import json
import anthropic
from dotenv import load_dotenv

# Загружаем .env явно
_env = os.path.join(os.path.dirname(__file__), '../../.env')
load_dotenv(_env, override=True)

from pipeline.agents.artem import search_social_trends
from pipeline.agents.petya import compare_trends_global_vs_russia
from pipeline.agents.avoska import analyze_tg_channels
from pipeline.agents.vova import analyze_marketplace
from pipeline.agents.polya import build_marketing_strategy, create_product_concept, analyze_competition_rf, package_insights_for_launch
from pipeline.agents import memory

# Ленивая инициализация — клиент создаётся при первом вызове
_client = None

def _get_client():
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            load_dotenv(_env, override=True)
            key = os.getenv("ANTHROPIC_API_KEY", "")
        _client = anthropic.Anthropic(api_key=key)
    return _client

SYSTEM_PROMPT = """Ты — Денис, операционный директор и главный оркестратор разведывательной системы NOTA.

NOTA — закрытый сервис для поиска FMCG-ниш в России. Твоя задача: помочь найти продуктовые возможности, которые можно запустить раньше других.

В твоём распоряжении четыре агента:
- **Артём** (тренд-разведчик) — ищет тренды в соцсетях (TikTok, LinkedIn, YouTube, X/Twitter, Reddit)
- **Петя** (SEO-аналитик) — сравнивает тренды глобально и в России (Яндекс, Google Trends, данные рынка)
- **Авоська** (FMCG гений) — анализирует профессиональные FMCG Telegram-каналы, находит инсайты из отрасли
- **Вова** (рыночный аналитик) — анализирует продажи, выручку, конкурентов на WB и Ozon через MPStats
- **Поля** (маркетолог) — упаковывает идеи и тренды в готовую маркетинговую стратегию для РФ: позиционирование, ICP, GTM, launch brief, конкурентный анализ

Правила:
- Отвечай на русском языке
- Используй агентов когда нужны данные — не придумывай их сам
- Синтезируй ответ кратко и по делу: что найдено, что значит для РФ
- Форматируй ответ СТРОГО для Telegram: используй только *жирный* через *звёздочки*, эмодзи, и обычный текст
- ЗАПРЕЩЕНО использовать: ##, ###, ---, **, markdown заголовки — Telegram их не рендерит как заголовки
- Структурируй через эмодзи-иконки вместо заголовков: 📊 Динамика рынка:, 💰 Цены:, 🏆 Бренды: и т.д.
- Если спрашивают о конкретном продукте/категории — запускай оба агента
- Если спрашивают о новостях FMCG, инсайтах из каналов, что происходит в отрасли — вызывай Авоську
- Если спрашивают о продажах на WB/Ozon, выручке категории, топ товарах, конкурентах на маркетплейсах — вызывай Вову
- Если спрашивают о маркетинге, позиционировании, упаковке продукта, GTM стратегии, конкурентах, как запустить продукт в России — вызывай Полю
- Если есть данные от других агентов (Артёма, Пети, Вовы) и нужен финальный launch brief — вызывай Полю с package_insights_for_launch
- Если вопрос общий/стратегический — отвечай сам без агентов
- В конце каждого аналитического ответа всегда указывай кто работал над ответом:
  🟢 Денис (опер. директор) • и перечисли агентов которых вызывал
- Финальный вывод: 🎯 **Вывод NOTA:**"""

TOOLS = [
    {
        "name": "search_social_trends",
        "description": "Артём (тренд-разведчик): ищет тренды в социальных сетях (TikTok, LinkedIn, YouTube, X/Twitter). Использовать когда нужно узнать что хайпует, что вирусится, какие продукты обсуждают в соцсетях.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Поисковый запрос на английском или русском. Например: 'protein bars trending USA' или 'протеиновые батончики тренд'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_marketplace",
        "description": "Вова (рыночный аналитик): анализирует реальные продажи, выручку, топ товаров и конкурентов на Wildberries и Ozon через MPStats API. Использовать когда спрашивают: сколько продаётся товар на WB/Ozon, какая выручка в категории, кто топ конкуренты, какие SKU лидируют, анализ маркетплейсов.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Название категории, продукта или SKU. Например: 'протеиновые батончики', 'снеки', '148471993'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_tg_channels",
        "description": "Авоська (FMCG гений): анализирует профессиональные FMCG Telegram-каналы и находит свежие инсайты, тренды и новости из российского FMCG рынка. Использовать когда спрашивают о новостях отрасли, что обсуждают в профессиональных каналах, инсайты недели, что происходит на рынке потребительских товаров.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Тема или фокус анализа. Например: 'протеиновые снеки' или '' для общего обзора"
                }
            },
            "required": []
        }
    },
    {
        "name": "compare_trends_global_vs_russia",
        "description": "Петя (SEO-аналитик): сравнивает тренд глобально и в России через Яндекс Search API, Google Trends и новостные источники. Использовать когда нужно понять — есть ли тренд в РФ, насколько он опережает или отстаёт от мирового.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Название продукта или категории. Например: 'protein bars' или 'колlagen drinks'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "build_marketing_strategy",
        "description": "Поля (маркетолог): разрабатывает маркетинговую стратегию для продукта/ниши под российский рынок. Использует позиционирование April Dunford, ICP, GTM-каналы для РФ. Использовать когда спрашивают: как запустить продукт в России, маркетинговая стратегия, позиционирование, целевая аудитория, GTM план.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Продукт или ниша. Например: 'протеиновые батончики' или 'коллагеновые напитки'"
                },
                "context": {
                    "type": "string",
                    "description": "Дополнительный контекст: данные от других агентов, тренды, рыночные данные"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "create_product_concept",
        "description": "Поля (маркетолог): создаёт концепцию продукта — название, УТП, ценовое позиционирование, launch checklist на 30 дней. Использовать когда нужно придумать как упаковать и назвать продукт для запуска на WB/Ozon.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_idea": {
                    "type": "string",
                    "description": "Идея продукта. Например: 'протеиновый батончик с матчей'"
                },
                "trend_data": {
                    "type": "string",
                    "description": "Данные о трендах от Артёма/Пети (опционально)"
                },
                "market_data": {
                    "type": "string",
                    "description": "Рыночные данные от Вовы (опционально)"
                }
            },
            "required": ["product_idea"]
        }
    },
    {
        "name": "analyze_competition_rf",
        "description": "Поля (маркетолог): конкурентный анализ категории на российском рынке — топ бренды, ценовые сегменты, позиционирование, слабые места конкурентов. Использовать когда спрашивают кто конкуренты, как они позиционируются, где ниша для входа.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Категория продукта. Например: 'протеиновые батончики' или 'функциональные напитки'"
                }
            },
            "required": ["category"]
        }
    },
    {
        "name": "package_insights_for_launch",
        "description": "Поля (маркетолог): собирает все данные от команды агентов в готовый launch brief — гипотеза, ЦА, позиционирование, каналы, план на 30 дней, риски. Использовать в конце полного анализа когда уже есть данные от Артёма, Пети, Вовы и нужен финальный маркетинговый план.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trend_summary": {
                    "type": "string",
                    "description": "Сводка данных от других агентов"
                },
                "category": {
                    "type": "string",
                    "description": "Категория продукта"
                }
            },
            "required": ["trend_summary", "category"]
        }
    }
]


def _call_tool(name: str, inputs: dict) -> str:
    if name == "search_social_trends":
        return search_social_trends(inputs["query"])
    elif name == "compare_trends_global_vs_russia":
        return compare_trends_global_vs_russia(inputs["query"])
    elif name == "analyze_tg_channels":
        return analyze_tg_channels(inputs.get("query", ""))
    elif name == "analyze_marketplace":
        return analyze_marketplace(inputs["query"])
    elif name == "build_marketing_strategy":
        return build_marketing_strategy(inputs["query"], inputs.get("context", ""))
    elif name == "create_product_concept":
        return create_product_concept(inputs["product_idea"], inputs.get("trend_data", ""), inputs.get("market_data", ""))
    elif name == "analyze_competition_rf":
        return analyze_competition_rf(inputs["category"])
    elif name == "package_insights_for_launch":
        return package_insights_for_launch(inputs["trend_summary"], inputs["category"])
    return "Инструмент не найден."


def ask_chukcha(chat_id: int, user_message: str) -> str:
    """
    Основная функция: принимает сообщение пользователя,
    возвращает ответ Чукчи (строка, Markdown для Telegram).
    """
    memory.add_message(chat_id, "user", user_message)
    messages = memory.get_history(chat_id)

    # Agentic loop: Claude может вызывать инструменты несколько раз
    loop_messages = list(messages)

    for _ in range(5):  # макс 5 итераций
        response = _get_client().messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=loop_messages,
        )

        # Если Claude хочет вызвать инструменты
        if response.stop_reason == "tool_use":
            # Добавляем ответ ассистента с tool_use блоками
            loop_messages.append({"role": "assistant", "content": response.content})

            # Выполняем все запрошенные инструменты
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"[Чукча] → вызывает {block.name}({block.input})")
                    result = _call_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            loop_messages.append({"role": "user", "content": tool_results})

        else:
            # Финальный ответ
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            memory.add_message(chat_id, "assistant", final_text)
            return final_text

    return "Чукча: что-то пошло не так, попробуй ещё раз."
