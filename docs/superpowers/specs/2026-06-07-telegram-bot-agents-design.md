# NOTA Telegram Bot — Multi-Agent System (v1)

## Goal
Telegram-бот с 3 агентами (Чукча, Артём, Петя) как основной интерфейс для поиска FMCG-трендов. Свободный чат — задаёшь вопрос, получаешь один структурированный ответ.

## Scope (v1 — эта итерация)
- Telegram Bot (python-telegram-bot)
- Чукча — оркестратор на Claude tool_use
- Артём — поиск в соцсетях (Exa: TikTok, LinkedIn, YouTube + Grok: X/Twitter)
- Петя — Google Trends + Яндекс.Вордстат (сравнение глобал vs РФ)
- Память диалога (последние 20 сообщений)
- Хостинг: Railway (бесплатный tier)

## Out of Scope (v1)
- Вова (Ozon/WB/Amazon) — следующая итерация
- ЯмакасиТудаси — следующая итерация
- VAPE-агент — отдельный проект
- Изменения в сайте NOTA

---

## Architecture

```
User → Telegram → Bot Handler
                      ↓
                 Чукча (Claude claude-sonnet, tool_use)
                      ↓ вызывает инструменты параллельно
          ┌───────────┴───────────┐
      Артём()                 Петя()
   Exa TikTok/LI          Google Trends
   Grok X/Twitter          Яндекс.Вордстат
          └───────────┬───────────┘
                      ↓
              Чукча синтезирует
                      ↓
             Telegram → ответ пользователю
                      ↓
             Supabase → сохраняем сигналы (опционально)
```

---

## Files Structure

```
pipeline/
  agents/
    __init__.py
    chukcha.py        # Оркестратор — Claude tool_use
    artem.py          # Поиск в соцсетях (Exa + Grok)
    petya.py          # Google Trends + Вордстат
    tools.py          # Описания инструментов для Claude
    memory.py         # История диалога (in-memory dict)
  
bot.py                # Telegram bot entry point
```

---

## Agent Details

### Чукча (chukcha.py)
- Model: claude-sonnet-4-5 (Anthropic SDK)
- Mode: tool_use — Claude сам решает когда и каких агентов вызвать
- System prompt: роль оркестратора, знает NOTA проект, отвечает на русском
- Инструменты: `search_social_trends`, `compare_trends_global_vs_russia`
- Память: последние 20 сообщений на пользователя (dict по chat_id)
- Ответ: форматированный Markdown для Telegram

### Артём (artem.py)
Функция `search_social_trends(query: str) -> str`

Источники:
1. Exa TikTok: `site:tiktok.com {query}` — 8 результатов
2. Exa LinkedIn: `site:linkedin.com {query} FMCG market` — 6 результатов
3. Exa YouTube: `site:youtube.com {query} trend review` — 5 результатов
4. Grok API: X/Twitter реальное время — `{query} trending` — если ключ есть

Возвращает: текст с найденными трендами и источниками

### Петя (petya.py)
Функция `compare_trends_global_vs_russia(query: str) -> str`

Источники:
1. `pytrends` — Google Trends (интерес по регионам: WW vs RU, динамика 12 мес)
2. Exa RU: яндекс/РБК/тасс поиск по теме
3. Exa EN: глобальный контекст

Wordstat: пока через Exa (поиск `wordstat {query}` на сайтах-агрегаторах) — прямой API требует модерацию Яндекса

Возвращает: текст с динамикой интереса глобально и в РФ

---

## Memory
```python
# memory.py
chat_histories: dict[int, list[dict]] = {}
MAX_MESSAGES = 20

def get_history(chat_id: int) -> list[dict]
def add_message(chat_id: int, role: str, content: str)
def clear_history(chat_id: int)
```

---

## Telegram Bot Commands
- (нет команд) — свободный чат, всё через Чукку
- `/start` — приветствие + инструкция
- `/clear` — очистить историю диалога

---

## Config (.env additions)
```
TELEGRAM_BOT_TOKEN=<токен от @BotFather>
ANTHROPIC_API_KEY=<ключ Claude API>
GROK_API_KEY=<ключ xAI, опционально>
```

---

## Hosting: Railway
- `railway up` → деплой
- Переменные через Railway dashboard
- Бесплатный tier: 500 часов/мес (хватит)
- `Procfile`: `worker: python bot.py`

---

## Data Flow Example
Пользователь: *"Что хайпует в протеиновых снеках в США?"*

1. Bot → history.add(user, "Что хайпует...")
2. Чукча (Claude) → решает вызвать Артёма
3. `search_social_trends("protein snacks USA trending")` → Exa + Grok
4. Чукча получает результат → формулирует ответ
5. history.add(assistant, ответ)
6. Bot → отправляет Markdown в Telegram

---

## Testing
- `tests/test_artem.py` — mock Exa, проверить форматирование
- `tests/test_petya.py` — mock pytrends, проверить парсинг
- `tests/test_chukcha.py` — mock Claude API, проверить tool_use flow
- `tests/test_memory.py` — проверить ротацию 20 сообщений
