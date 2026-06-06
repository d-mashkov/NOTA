# NOTA Python Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Заменить Make.com на надёжный Python-скрипт, который еженедельно генерирует NOTы: читает категории из Supabase → ищет тренды через Exa.ai (EN+RU) → анализирует Telegram-данные → отправляет в Gemini → сохраняет результат в Supabase.

**Architecture:** Один Python-скрипт `pipeline/run.py` с модулями для каждого шага. Каждый модуль независим и тестируем отдельно. Запуск — вручную или через GitHub Actions по расписанию (cron еженедельно).

**Tech Stack:** Python 3.11+, `supabase-py`, `requests`, `python-dotenv`, `pytest`

---

## Структура файлов

```
nota/
├── pipeline/
│   ├── __init__.py
│   ├── run.py              # точка входа, оркестратор
│   ├── config.py           # переменные окружения
│   ├── supabase_client.py  # чтение категорий, запись нот
│   ├── exa_client.py       # поиск трендов через Exa.ai
│   ├── telegram_loader.py  # загрузка и поиск по Telegram JSON
│   ├── gemini_client.py    # вызов Gemini API
│   └── prompt.py           # сборка промпта для Gemini
├── data/
│   └── telegram/           # сюда кладём экспортированные JSON из Telegram
├── tests/
│   ├── test_exa_client.py
│   ├── test_gemini_client.py
│   ├── test_telegram_loader.py
│   ├── test_prompt.py
│   └── test_supabase_client.py
├── .env.example
├── requirements.txt
└── .github/
    └── workflows/
        └── weekly-pipeline.yml
```

---

## Task 1: Настройка проекта и зависимости

**Files:**
- Create: `pipeline/__init__.py`
- Create: `pipeline/config.py`
- Create: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: Создать requirements.txt**

```
supabase==2.10.0
requests==2.32.3
python-dotenv==1.0.1
pytest==8.3.4
pytest-mock==3.14.0
```

- [ ] **Step 2: Создать .env.example**

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_...
EXA_API_KEY=your-exa-key
GEMINI_API_KEY=AIza...
```

- [ ] **Step 3: Создать .env (реальные ключи, не коммитить)**

```
SUPABASE_URL=https://rizvgldb1ytk90ch1a9ig.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_B6YUFjsNvm3hBWULHVO4jg_VzxATktg
EXA_API_KEY=43aefed6-8014-4992-bbad-12d42fa7a06e
GEMINI_API_KEY=<вставить свежий ключ с aistudio.google.com>
```

- [ ] **Step 4: Создать pipeline/config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
EXA_API_KEY = os.environ["EXA_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

EXA_API_URL = "https://api.exa.ai/search"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

EXA_NUM_RESULTS = 10
EXA_DAYS_BACK = 365
```

- [ ] **Step 5: Создать pipeline/__init__.py**

```python
# NOTA Pipeline
```

- [ ] **Step 6: Установить зависимости**

```bash
cd /Users/denismaskov/nota
pip install -r requirements.txt
```

Ожидаемый вывод: `Successfully installed supabase-... requests-... python-dotenv-...`

- [ ] **Step 7: Добавить .env в .gitignore**

```bash
echo ".env" >> .gitignore
echo "data/telegram/*.json" >> .gitignore
```

- [ ] **Step 8: Коммит**

```bash
git add pipeline/ requirements.txt .env.example .gitignore
git commit -m "feat: init python pipeline structure"
```

---

## Task 2: Supabase Client — чтение категорий

**Files:**
- Create: `pipeline/supabase_client.py`
- Create: `tests/test_supabase_client.py`

- [ ] **Step 1: Написать тест**

```python
# tests/test_supabase_client.py
from unittest.mock import patch, MagicMock
from pipeline.supabase_client import get_active_categories

def test_get_active_categories_returns_list():
    mock_response = MagicMock()
    mock_response.data = [
        {"id": "uuid-1", "name": "ПП батончики", "name_en": "Protein bars", "seed_queries": ["пп батончик"]},
        {"id": "uuid-2", "name": "Функциональные напитки", "name_en": "Functional drinks", "seed_queries": ["функциональный напиток"]},
    ]
    with patch("pipeline.supabase_client.supabase") as mock_sb:
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        result = get_active_categories()
    assert len(result) == 2
    assert result[0]["name"] == "ПП батончики"

def test_get_active_categories_empty():
    mock_response = MagicMock()
    mock_response.data = []
    with patch("pipeline.supabase_client.supabase") as mock_sb:
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        result = get_active_categories()
    assert result == []
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
cd /Users/denismaskov/nota
pytest tests/test_supabase_client.py -v
```

Ожидаемый вывод: `ImportError: cannot import name 'get_active_categories'`

- [ ] **Step 3: Реализовать supabase_client.py**

```python
# pipeline/supabase_client.py
from supabase import create_client
from pipeline.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_active_categories() -> list[dict]:
    """Возвращает список активных категорий из Supabase."""
    response = (
        supabase.table("categories")
        .select("id, name, name_en, seed_queries")
        .eq("is_active", True)
        .execute()
    )
    return response.data


def save_note(category_id: str, note_data: dict) -> str:
    """Сохраняет NOTу в таблицу notes. Возвращает id новой записи."""
    row = {
        "title": note_data["title"],
        "category_id": category_id,
        "description": note_data["description"],
        "score": note_data["score_breakdown"]["total"],
        "status": "published",
        "trend_stage": note_data["trend_stage"],
        "competition_level": note_data["competition_level"],
        "recommendation": note_data["recommendation"],
    }
    response = supabase.table("notes").insert(row).execute()
    return response.data[0]["id"]


def save_note_report(note_id: str, report: dict) -> None:
    """Сохраняет детальный отчёт в таблицу note_reports."""
    row = {
        "note_id": note_id,
        "foreign_cases": report.get("foreign_cases"),
        "demand_russia": report.get("demand_russia"),
        "demand_global": report.get("demand_global"),
        "russian_market": report.get("russian_market"),
        "competitors": report.get("competitors"),
        "product_hypothesis": report.get("product_hypothesis"),
        "target_audience": report.get("target_audience"),
        "flavors_formats": report.get("flavors_formats"),
        "market_size": report.get("market_size"),
        "launch_difficulty": report.get("launch_difficulty"),
        "potential_margin": report.get("potential_margin"),
        "risks": report.get("risks"),
        "gtm": report.get("gtm"),
        "ai_output": report.get("ai_output"),
        "ai_recommendation": report.get("ai_recommendation"),
        "sources": report.get("sources"),
    }
    supabase.table("note_reports").insert(row).execute()
```

- [ ] **Step 4: Запустить тест — убедиться что проходит**

```bash
pytest tests/test_supabase_client.py -v
```

Ожидаемый вывод: `2 passed`

- [ ] **Step 5: Коммит**

```bash
git add pipeline/supabase_client.py tests/test_supabase_client.py
git commit -m "feat: supabase client for reading categories and saving notes"
```

---

## Task 3: Exa.ai Client — поиск трендов

**Files:**
- Create: `pipeline/exa_client.py`
- Create: `tests/test_exa_client.py`

- [ ] **Step 1: Написать тест**

```python
# tests/test_exa_client.py
from unittest.mock import patch, MagicMock
from pipeline.exa_client import search_trends

def test_search_trends_returns_titles():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"title": "Protein bar market growing", "url": "https://example.com", "text": "Long article..."},
            {"title": "Keto bars trend 2024", "url": "https://example2.com", "text": "Another article..."},
        ]
    }
    with patch("pipeline.exa_client.requests.post", return_value=mock_response):
        result = search_trends("protein bars", lang="en")
    assert len(result) == 2
    assert result[0]["title"] == "Protein bar market growing"
    assert "url" in result[0]
    assert "text" in result[0]

def test_search_trends_empty_results():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    with patch("pipeline.exa_client.requests.post", return_value=mock_response):
        result = search_trends("unknown niche xyz", lang="ru")
    assert result == []
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/test_exa_client.py -v
```

- [ ] **Step 3: Реализовать exa_client.py**

```python
# pipeline/exa_client.py
import requests
from datetime import datetime, timedelta
from pipeline.config import EXA_API_KEY, EXA_API_URL, EXA_NUM_RESULTS, EXA_DAYS_BACK


def search_trends(query: str, lang: str = "en") -> list[dict]:
    """
    Ищет тренды через Exa.ai neural search.
    lang="en" — глобальные тренды, lang="ru" — российский рынок.
    Возвращает список результатов с полями: title, url, text.
    """
    date_from = (datetime.now() - timedelta(days=EXA_DAYS_BACK)).strftime("%Y-%m-%dT00:00:00Z")

    payload = {
        "query": query,
        "numResults": EXA_NUM_RESULTS,
        "startPublishedDate": date_from,
        "contents": {
            "text": {"maxCharacters": 2000}
        }
    }

    if lang == "ru":
        payload["includeDomains"] = [
            "vc.ru", "retail.ru", "foodretail.ru", "rb.ru",
            "habr.com", "rbc.ru", "kommersant.ru"
        ]

    response = requests.post(
        EXA_API_URL,
        json=payload,
        headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def format_results_for_prompt(results: list[dict]) -> str:
    """Форматирует результаты Exa.ai в текст для промпта Gemini."""
    if not results:
        return "Данные не найдены."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "—")
        url = r.get("url", "")
        text = r.get("text", "")[:500].replace('"', "'")
        lines.append(f"{i}. {title}\n   URL: {url}\n   {text}")
    return "\n\n".join(lines)
```

- [ ] **Step 4: Запустить тест**

```bash
pytest tests/test_exa_client.py -v
```

Ожидаемый вывод: `2 passed`

- [ ] **Step 5: Коммит**

```bash
git add pipeline/exa_client.py tests/test_exa_client.py
git commit -m "feat: exa.ai client for EN and RU trend search"
```

---

## Task 4: Telegram Loader — загрузка данных из каналов

**Files:**
- Create: `pipeline/telegram_loader.py`
- Create: `tests/test_telegram_loader.py`
- Create: `data/telegram/.gitkeep`

- [ ] **Step 1: Написать тест**

```python
# tests/test_telegram_loader.py
import json
import tempfile
import os
from pipeline.telegram_loader import load_telegram_posts, search_relevant_posts

SAMPLE_TELEGRAM_EXPORT = {
    "name": "FMCG Report",
    "messages": [
        {
            "id": 1,
            "type": "message",
            "date": "2025-06-01T10:00:00",
            "text": "Протеиновые батончики — тренд 2025. Рост продаж на 40% за год.",
            "views": 1500,
            "forwards": 23
        },
        {
            "id": 2,
            "type": "message",
            "date": "2025-05-15T12:00:00",
            "text": "Функциональные напитки захватывают российский рынок.",
            "views": 890,
            "forwards": 12
        },
        {
            "id": 3,
            "type": "service",
            "date": "2025-05-01T00:00:00",
            "text": ""
        }
    ]
}

def test_load_telegram_posts():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE_TELEGRAM_EXPORT, f, ensure_ascii=False)
        tmp_path = f.name
    try:
        posts = load_telegram_posts(tmp_path)
        assert len(posts) == 2  # service message отфильтрован
        assert posts[0]["text"] == "Протеиновые батончики — тренд 2025. Рост продаж на 40% за год."
        assert posts[0]["channel"] == "FMCG Report"
    finally:
        os.unlink(tmp_path)

def test_search_relevant_posts():
    posts = [
        {"channel": "FMCG Report", "date": "2025-06-01", "text": "Протеиновые батончики растут на 40%", "views": 1500},
        {"channel": "FMCG Report", "date": "2025-05-01", "text": "Функциональные напитки захватывают рынок", "views": 890},
        {"channel": "FMCG Report", "date": "2025-04-01", "text": "Зефир классический — стагнация", "views": 200},
    ]
    results = search_relevant_posts(posts, keywords=["батончик", "протеин"])
    assert len(results) == 1
    assert "батончики" in results[0]["text"]
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/test_telegram_loader.py -v
```

- [ ] **Step 3: Реализовать telegram_loader.py**

```python
# pipeline/telegram_loader.py
import json
import os
from pathlib import Path

TELEGRAM_DATA_DIR = Path(__file__).parent.parent / "data" / "telegram"


def load_telegram_posts(filepath: str) -> list[dict]:
    """
    Загружает посты из Telegram JSON-экспорта.
    Фильтрует служебные сообщения и пустые тексты.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    channel_name = data.get("name", "Unknown")
    posts = []

    for msg in data.get("messages", []):
        if msg.get("type") != "message":
            continue
        text = msg.get("text", "")
        # text может быть строкой или списком (когда есть форматирование)
        if isinstance(text, list):
            text = " ".join(part if isinstance(part, str) else part.get("text", "") for part in text)
        if not text.strip():
            continue
        posts.append({
            "channel": channel_name,
            "date": msg.get("date", "")[:10],
            "text": text.strip(),
            "views": msg.get("views", 0),
            "forwards": msg.get("forwards", 0),
        })

    return posts


def load_all_telegram_posts() -> list[dict]:
    """Загружает все JSON-файлы из data/telegram/."""
    all_posts = []
    if not TELEGRAM_DATA_DIR.exists():
        return []
    for file in TELEGRAM_DATA_DIR.glob("*.json"):
        all_posts.extend(load_telegram_posts(str(file)))
    return all_posts


def search_relevant_posts(posts: list[dict], keywords: list[str]) -> list[dict]:
    """
    Ищет посты, содержащие хотя бы одно из ключевых слов (без учёта регистра).
    Возвращает отсортированные по views (наиболее просматриваемые первыми).
    """
    keywords_lower = [kw.lower() for kw in keywords]
    relevant = [
        p for p in posts
        if any(kw in p["text"].lower() for kw in keywords_lower)
    ]
    return sorted(relevant, key=lambda p: p.get("views", 0), reverse=True)


def format_telegram_for_prompt(posts: list[dict], max_posts: int = 5) -> str:
    """Форматирует Telegram-посты в текст для промпта."""
    if not posts:
        return "Данные из Telegram-каналов не найдены."
    lines = []
    for p in posts[:max_posts]:
        lines.append(f"[{p['channel']} | {p['date']} | 👁 {p.get('views', 0)}]\n{p['text']}")
    return "\n\n".join(lines)
```

- [ ] **Step 4: Создать data/telegram/.gitkeep**

```bash
mkdir -p /Users/denismaskov/nota/data/telegram
touch /Users/denismaskov/nota/data/telegram/.gitkeep
```

- [ ] **Step 5: Запустить тест**

```bash
pytest tests/test_telegram_loader.py -v
```

Ожидаемый вывод: `2 passed`

- [ ] **Step 6: Коммит**

```bash
git add pipeline/telegram_loader.py tests/test_telegram_loader.py data/telegram/.gitkeep
git commit -m "feat: telegram JSON loader with keyword search"
```

---

## Task 5: Prompt Builder — сборка промпта для Gemini

**Files:**
- Create: `pipeline/prompt.py`
- Create: `tests/test_prompt.py`

- [ ] **Step 1: Написать тест**

```python
# tests/test_prompt.py
from pipeline.prompt import build_prompt

def test_build_prompt_contains_category():
    prompt = build_prompt(
        category_name="ПП батончики",
        category_name_en="Protein bars",
        exa_en_data="1. Protein bars growing fast\n   URL: https://example.com",
        exa_ru_data="1. Батончики без сахара в тренде\n   URL: https://vc.ru",
        telegram_data="[FMCG Report | 2025-06-01 | 👁 1500]\nПротеиновые батончики растут.",
    )
    assert "ПП батончики" in prompt
    assert "Protein bars" in prompt
    assert "Protein bars growing fast" in prompt
    assert "Батончики без сахара" in prompt
    assert "FMCG Report" in prompt
    assert "demand_russia_growth" in prompt
    assert "total" in prompt

def test_build_prompt_without_telegram():
    prompt = build_prompt(
        category_name="Зефир",
        category_name_en="Marshmallow",
        exa_en_data="Some EN data",
        exa_ru_data="Some RU data",
        telegram_data="",
    )
    assert "Зефир" in prompt
    assert isinstance(prompt, str)
    assert len(prompt) > 500
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/test_prompt.py -v
```

- [ ] **Step 3: Реализовать prompt.py**

```python
# pipeline/prompt.py
from datetime import date


def build_prompt(
    category_name: str,
    category_name_en: str,
    exa_en_data: str,
    exa_ru_data: str,
    telegram_data: str,
) -> str:
    today = date.today().strftime("%Y-%m-%d")

    telegram_section = ""
    if telegram_data:
        telegram_section = f"\n\n### Данные из Telegram-каналов (FMCG-аналитика РФ):\n{telegram_data}"

    return f"""Ты — аналитик FMCG-рынка России. На основе данных о трендах создай структурированный отчёт по продуктовой нише (NOTA).

Отвечай ТОЛЬКО валидным JSON без markdown-обёртки, без ```json, только чистый JSON.

Категория: {category_name} ({category_name_en})
Дата анализа: {today}

### Данные Exa.ai (глобальные тренды EN):
{exa_en_data}

### Данные Exa.ai (тренды РФ):
{exa_ru_data}{telegram_section}

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
```

- [ ] **Step 4: Запустить тест**

```bash
pytest tests/test_prompt.py -v
```

Ожидаемый вывод: `2 passed`

- [ ] **Step 5: Коммит**

```bash
git add pipeline/prompt.py tests/test_prompt.py
git commit -m "feat: prompt builder with Exa + Telegram data"
```

---

## Task 6: Gemini Client — вызов API

**Files:**
- Create: `pipeline/gemini_client.py`
- Create: `tests/test_gemini_client.py`

- [ ] **Step 1: Написать тест**

```python
# tests/test_gemini_client.py
import json
from unittest.mock import patch, MagicMock
from pipeline.gemini_client import generate_nota

SAMPLE_GEMINI_RESPONSE = {
    "candidates": [{
        "content": {
            "parts": [{
                "text": json.dumps({
                    "title": "ПП батончики без сахара",
                    "description": "Растущий сегмент...",
                    "trend_stage": "growing",
                    "competition_level": "medium",
                    "recommendation": "launch",
                    "report": {
                        "foreign_cases": "Kind bars, RxBar...",
                        "demand_russia": "Рост 35% г/г...",
                        "demand_global": "США лидер...",
                        "russian_market": "BioFoodLab, Bite...",
                        "competitors": [{"name": "Bite", "segment": "масс-маркет", "price_range": "80-120 руб"}],
                        "target_audience": "25-35 лет...",
                        "product_hypothesis": "Батончик с финиками...",
                        "flavors_formats": "Шоколад, арахис...",
                        "market_size": "15 млрд руб/год",
                        "launch_difficulty": "medium. Нужен технолог.",
                        "potential_margin": "Цена 150р, себес 60р, маржа 60%",
                        "risks": "Конкуренция высокая",
                        "gtm": "WB, Ozon, ВкусВилл",
                        "ai_output": "Перспективная ниша...",
                        "ai_recommendation": "Запускать в Q3 2025",
                        "sources": [{"title": "Exa search", "url": "", "type": "exa"}]
                    },
                    "score_breakdown": {
                        "demand_russia_growth": 18,
                        "foreign_confirmation": 14,
                        "marketplace_sales": 12,
                        "low_competition": 8,
                        "launch_simplicity": 7,
                        "potential_margin": 9,
                        "media_buzz": 8,
                        "fmcg_fit": 5,
                        "total": 81
                    }
                }, ensure_ascii=False)
            }]
        }
    }]
}

def test_generate_nota_returns_dict():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_GEMINI_RESPONSE
    with patch("pipeline.gemini_client.requests.post", return_value=mock_response):
        result = generate_nota("Test prompt about protein bars")
    assert result["title"] == "ПП батончики без сахара"
    assert result["score_breakdown"]["total"] == 81
    assert result["recommendation"] == "launch"

def test_generate_nota_raises_on_api_error():
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = Exception("Quota exceeded")
    with patch("pipeline.gemini_client.requests.post", return_value=mock_response):
        try:
            generate_nota("Test prompt")
            assert False, "Should have raised"
        except Exception as e:
            assert "Quota exceeded" in str(e)
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/test_gemini_client.py -v
```

- [ ] **Step 3: Реализовать gemini_client.py**

```python
# pipeline/gemini_client.py
import json
import requests
from pipeline.config import GEMINI_API_KEY, GEMINI_API_URL


def generate_nota(prompt: str) -> dict:
    """
    Отправляет промпт в Gemini API и возвращает распарсенный JSON с NOTой.
    Выбрасывает исключение если API недоступен или вернул невалидный JSON.
    """
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
    }

    response = requests.post(
        GEMINI_API_URL,
        json=payload,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()

    raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]

    # Убираем возможные markdown-обёртки (на случай если модель добавила ```json)
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
    if raw_text.endswith("```"):
        raw_text = raw_text.rsplit("```", 1)[0]

    return json.loads(raw_text)
```

- [ ] **Step 4: Запустить тест**

```bash
pytest tests/test_gemini_client.py -v
```

Ожидаемый вывод: `2 passed`

- [ ] **Step 5: Коммит**

```bash
git add pipeline/gemini_client.py tests/test_gemini_client.py
git commit -m "feat: gemini client with JSON parsing and markdown cleanup"
```

---

## Task 7: Оркестратор — pipeline/run.py

**Files:**
- Create: `pipeline/run.py`

- [ ] **Step 1: Реализовать run.py**

```python
# pipeline/run.py
import sys
import traceback
from datetime import date
from pipeline.supabase_client import get_active_categories, save_note, save_note_report
from pipeline.exa_client import search_trends, format_results_for_prompt
from pipeline.telegram_loader import load_all_telegram_posts, search_relevant_posts, format_telegram_for_prompt
from pipeline.prompt import build_prompt
from pipeline.gemini_client import generate_nota


def run_pipeline(dry_run: bool = False) -> None:
    """
    Основной пайплайн NOTA.
    dry_run=True — печатает результат без сохранения в Supabase.
    """
    print(f"🚀 NOTA Pipeline started | {date.today()} | dry_run={dry_run}")

    # Загружаем Telegram-данные один раз для всех категорий
    telegram_posts = load_all_telegram_posts()
    print(f"📱 Telegram posts loaded: {len(telegram_posts)}")

    categories = get_active_categories()
    print(f"📋 Categories to process: {len(categories)}")

    success_count = 0
    error_count = 0

    for category in categories:
        cat_name = category["name"]
        cat_name_en = category.get("name_en") or cat_name
        cat_id = category["id"]
        keywords = category.get("seed_queries") or [cat_name]

        print(f"\n▶ Processing: {cat_name}")

        try:
            # 1. Exa.ai поиск
            print("  🔍 Searching Exa EN...")
            exa_en = search_trends(f"{cat_name_en} market trends Russia FMCG", lang="en")
            exa_en_text = format_results_for_prompt(exa_en)

            print("  🔍 Searching Exa RU...")
            exa_ru = search_trends(" ".join(keywords[:3]), lang="ru")
            exa_ru_text = format_results_for_prompt(exa_ru)

            # 2. Telegram
            relevant_tg = search_relevant_posts(telegram_posts, keywords=keywords)
            tg_text = format_telegram_for_prompt(relevant_tg)
            print(f"  📱 Telegram matches: {len(relevant_tg)}")

            # 3. Промпт и Gemini
            prompt = build_prompt(
                category_name=cat_name,
                category_name_en=cat_name_en,
                exa_en_data=exa_en_text,
                exa_ru_data=exa_ru_text,
                telegram_data=tg_text,
            )

            print("  🤖 Calling Gemini...")
            nota = generate_nota(prompt)
            score = nota["score_breakdown"]["total"]
            print(f"  ✅ NOTA generated: {nota['title']} | score={score} | {nota['recommendation']}")

            # 4. Сохранение
            if not dry_run:
                note_id = save_note(cat_id, nota)
                save_note_report(note_id, nota["report"])
                print(f"  💾 Saved to Supabase: note_id={note_id}")
            else:
                print(f"  [dry_run] Skipping save.")

            success_count += 1

        except Exception as e:
            print(f"  ❌ Error processing {cat_name}: {e}")
            traceback.print_exc()
            error_count += 1

    print(f"\n✅ Done. Success: {success_count} | Errors: {error_count}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_pipeline(dry_run=dry_run)
```

- [ ] **Step 2: Запустить dry-run**

```bash
cd /Users/denismaskov/nota
python -m pipeline.run --dry-run
```

Ожидаемый вывод (примерно):
```
🚀 NOTA Pipeline started | 2026-06-07 | dry_run=True
📱 Telegram posts loaded: 0
📋 Categories to process: 3
▶ Processing: ПП батончики
  🔍 Searching Exa EN...
  🔍 Searching Exa RU...
  📱 Telegram matches: 0
  🤖 Calling Gemini...
  ✅ NOTA generated: ... | score=XX | launch
  [dry_run] Skipping save.
...
✅ Done. Success: 3 | Errors: 0
```

- [ ] **Step 3: Если успешно — запустить реальный прогон**

```bash
python -m pipeline.run
```

- [ ] **Step 4: Коммит**

```bash
git add pipeline/run.py
git commit -m "feat: pipeline orchestrator with dry-run mode"
```

---

## Task 8: GitHub Actions — автозапуск раз в неделю

**Files:**
- Create: `.github/workflows/weekly-pipeline.yml`

- [ ] **Step 1: Создать workflow**

```yaml
# .github/workflows/weekly-pipeline.yml
name: NOTA Weekly Pipeline

on:
  schedule:
    - cron: '0 6 * * 1'  # каждый понедельник в 6:00 UTC (9:00 МСК)
  workflow_dispatch:       # ручной запуск из GitHub UI

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run NOTA pipeline
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          EXA_API_KEY: ${{ secrets.EXA_API_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python -m pipeline.run
```

- [ ] **Step 2: Добавить секреты в GitHub**

Перейди на github.com → твой репо → Settings → Secrets → Actions → New secret:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `EXA_API_KEY`
- `GEMINI_API_KEY`

- [ ] **Step 3: Запустить вручную для проверки**

GitHub → Actions → "NOTA Weekly Pipeline" → Run workflow

- [ ] **Step 4: Коммит**

```bash
git add .github/workflows/weekly-pipeline.yml
git commit -m "feat: github actions weekly pipeline cron"
```

---

## Итог

После выполнения всех задач пайплайн будет:
- ✅ Читать категории из Supabase
- ✅ Искать тренды через Exa.ai (EN + RU)
- ✅ Использовать Telegram-данные (загружаешь JSON вручную в `data/telegram/`)
- ✅ Генерировать NOTы через Gemini
- ✅ Сохранять в Supabase (notes + note_reports)
- ✅ Запускаться автоматически каждый понедельник

**Чтобы загрузить Telegram данные:** экспортируй историю канала в Telegram Desktop (Settings → Advanced → Export Telegram data → JSON) и положи файл в `data/telegram/`.
