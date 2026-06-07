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

В твоём распоряжении три агента:
- **Артём** (тренд-разведчик) — ищет тренды в соцсетях (TikTok, LinkedIn, YouTube, X/Twitter)
- **Петя** (SEO-аналитик) — сравнивает тренды глобально и в России (Яндекс, Google Trends, данные рынка)
- **Авоська** (FMCG гений) — анализирует профессиональные FMCG Telegram-каналы, находит инсайты из отрасли

Правила:
- Отвечай на русском языке
- Используй агентов когда нужны данные — не придумывай их сам
- Синтезируй ответ кратко и по делу: что найдено, что значит для РФ
- Форматируй ответ для Telegram (Markdown, эмодзи уместно)
- Если спрашивают о конкретном продукте/категории — запускай оба агента
- Если спрашивают о новостях FMCG, инсайтах из каналов, что происходит в отрасли — вызывай Авоську
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
    }
]


def _call_tool(name: str, inputs: dict) -> str:
    if name == "search_social_trends":
        return search_social_trends(inputs["query"])
    elif name == "compare_trends_global_vs_russia":
        return compare_trends_global_vs_russia(inputs["query"])
    elif name == "analyze_tg_channels":
        return analyze_tg_channels(inputs.get("query", ""))
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
