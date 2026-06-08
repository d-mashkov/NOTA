"""
Агент Вова — рыночный аналитик маркетплейсов.
Источники: WB + Ozon через MPStats API.
Анализирует продажи, выручку, конкурентов, тренды категорий.
"""

import os
import requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'), override=True)

BASE_URL = "https://mpstats.io/api"
HEADERS = {
    "Content-Type": "application/json",
}


def _token() -> str:
    return os.getenv("MPSTATS_TOKEN", "")


def _get(path: str, params: dict = None) -> dict:
    """GET-запрос к MPStats API."""
    token = _token()
    if not token:
        return None
    try:
        r = requests.get(
            f"{BASE_URL}{path}",
            params=params or {},
            headers={**HEADERS, "X-Mpstats-TOKEN": token},
            timeout=15,
        )
        if r.status_code == 401:
            print("[Вова] ❌ Неверный токен MPStats")
            return None
        if r.status_code == 403:
            print("[Вова] ❌ Нет доступа — проверь тариф MPStats (нужен тариф с API)")
            return None
        if r.status_code == 429:
            print("[Вова] ⚠️ Rate limit MPStats — слишком много запросов")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[Вова] Ошибка запроса {path}: {e}")
        return None


def _post(path: str, body: dict, params: dict = None) -> dict:
    """POST-запрос к MPStats API."""
    token = _token()
    if not token:
        return None
    try:
        r = requests.post(
            f"{BASE_URL}{path}",
            json=body,
            params=params or {},
            headers={**HEADERS, "X-Mpstats-TOKEN": token},
            timeout=15,
        )
        if r.status_code in (401, 403):
            print(f"[Вова] ❌ Нет доступа ({r.status_code}) — проверь токен и тариф")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[Вова] Ошибка запроса {path}: {e}")
        return None


def _dates(days_back: int = 30) -> tuple[str, str]:
    """Возвращает (d1, d2) — период анализа."""
    d2 = date.today()
    d1 = d2 - timedelta(days=days_back)
    return d1.isoformat(), d2.isoformat()


# ──────────────────────────────────────────────
# WB — категории и товары
# ──────────────────────────────────────────────

def wb_category(category_path: str, days: int = 30) -> str:
    """
    Анализ категории WB — топ товаров, выручка, тренды.
    category_path: например 'Продукты питания/Снеки и чипсы'
    """
    d1, d2 = _dates(days)
    print(f"[Вова] WB категория: {category_path}")

    data = _post(
        "/wb/get/category",
        body={"startRow": 0, "endRow": 20},
        params={"d1": d1, "d2": d2, "path": category_path},
    )
    if not data:
        return f"Вова: нет данных по категории '{category_path}'"

    items = data.get("data", [])
    if not items:
        return f"Вова: категория '{category_path}' пуста или не найдена"

    # Считаем агрегаты
    total_revenue = sum(i.get("revenue", 0) for i in items)
    total_sales = sum(i.get("sales", 0) for i in items)
    avg_price = sum(i.get("final_price", 0) for i in items) / len(items) if items else 0

    lines = [
        f"📦 **WB: {category_path}** (за {days} дней)\n",
        f"💰 Суммарная выручка топ-20: **{total_revenue:,.0f} ₽**",
        f"📦 Продаж: **{total_sales:,} шт**",
        f"💵 Средняя цена: **{avg_price:,.0f} ₽**\n",
        "**Топ-10 товаров по выручке:**",
    ]

    sorted_items = sorted(items, key=lambda x: x.get("revenue", 0), reverse=True)
    for i, item in enumerate(sorted_items[:10], 1):
        name = item.get("name", "—")[:55]
        revenue = item.get("revenue", 0)
        sales = item.get("sales", 0)
        price = item.get("final_price", 0)
        brand = item.get("brand", "")
        feedbacks = item.get("comments", 0)
        lines.append(
            f"{i}. **{name}**\n"
            f"   {brand} | {price:,.0f}₽ | {sales} шт | {revenue:,.0f}₽ выручки | ⭐{feedbacks} отз"
        )

    return "\n".join(lines)


def wb_item(sku: str, days: int = 30) -> str:
    """Детальный анализ товара WB по SKU."""
    d1, d2 = _dates(days)
    print(f"[Вова] WB товар SKU: {sku}")

    data = _get(f"/wb/get/item/{sku}/sales", params={"d1": d1, "d2": d2})
    if not data:
        return f"Вова: нет данных по SKU {sku}"

    sales_data = data if isinstance(data, list) else data.get("data", [])
    total_sales = sum(d.get("sales", 0) for d in sales_data)
    total_revenue = sum(d.get("revenue", 0) for d in sales_data)

    return (
        f"📦 **WB SKU {sku}** (за {days} дней)\n"
        f"📦 Продаж: **{total_sales:,} шт**\n"
        f"💰 Выручка: **{total_revenue:,.0f} ₽**"
    )


def wb_keywords(query: str) -> str:
    """Поисковые запросы WB — частотность и тренды."""
    print(f"[Вова] WB ключи: {query}")

    data = _post("/wb/get/keywords/bloom", body={"keywords": [query]})
    if not data:
        return ""

    keywords = data if isinstance(data, list) else data.get("data", [])
    if not keywords:
        return ""

    lines = [f"🔍 **WB ключевые слова по '{query}':**\n"]
    for kw in sorted(keywords, key=lambda x: x.get("wbWbCount", 0), reverse=True)[:10]:
        word = kw.get("keyword", "")
        freq = kw.get("wbWbCount", 0)
        trend = kw.get("trend", 0)
        trend_arrow = "↑" if trend > 0 else ("↓" if trend < 0 else "→")
        lines.append(f"• **{word}** — {freq:,} запросов/мес {trend_arrow}")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Ozon
# ──────────────────────────────────────────────

def ozon_category(category_path: str, days: int = 30) -> str:
    """Анализ категории Ozon."""
    d1, d2 = _dates(days)
    print(f"[Вова] Ozon категория: {category_path}")

    data = _post(
        "/oz/get/category",
        body={"startRow": 0, "endRow": 20},
        params={"d1": d1, "d2": d2, "path": category_path},
    )
    if not data:
        return f"Вова: нет данных Ozon по '{category_path}'"

    items = data.get("data", [])
    if not items:
        return f"Вова: категория Ozon '{category_path}' пуста"

    total_revenue = sum(i.get("revenue", 0) for i in items)
    total_sales = sum(i.get("sales", 0) for i in items)

    lines = [
        f"🟦 **Ozon: {category_path}** (за {days} дней)\n",
        f"💰 Выручка топ-20: **{total_revenue:,.0f} ₽**",
        f"📦 Продаж: **{total_sales:,} шт**\n",
        "**Топ-10 товаров:**",
    ]

    for i, item in enumerate(
        sorted(items, key=lambda x: x.get("revenue", 0), reverse=True)[:10], 1
    ):
        name = item.get("name", "—")[:55]
        revenue = item.get("revenue", 0)
        sales = item.get("sales", 0)
        price = item.get("final_price", 0)
        lines.append(
            f"{i}. **{name}** | {price:,.0f}₽ | {sales} шт | {revenue:,.0f}₽"
        )

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Fallback через Grok (без MPStats токена)
# ──────────────────────────────────────────────

def _grok_marketplace(query: str) -> str:
    """Ищет аналитику WB/Ozon через Grok web_search из открытых отчётов."""
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
                "input": [{"role": "user", "content": (
                    f"Найди аналитику продаж на Wildberries и Ozon по теме: {query}\n\n"
                    "Ищи данные из: MPStats блог, MarketGuru, Data Insight, официальные отчёты WB/Ozon, аналитические статьи.\n\n"
                    "Покажи на русском:\n"
                    "• Объём категории в рублях (если найдёшь)\n"
                    "• Топ бренды/товары с цифрами продаж\n"
                    "• Динамика роста/падения категории\n"
                    "• Средние цены на WB и Ozon\n"
                    "• Количество продавцов в нише\n"
                    "• Вывод: перспективна ли ниша\n\n"
                    "Указывай источник и дату данных. Максимум 350 слов."
                )}],
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
        print(f"[Вова] Grok fallback error: {e}")
        return ""


# ──────────────────────────────────────────────
# Главная функция для Дениса (оркестратор)
# ──────────────────────────────────────────────

def analyze_marketplace(query: str) -> str:
    """
    Анализирует маркетплейсы WB + Ozon по теме/категории/SKU.
    Если есть MPSTATS_TOKEN — использует прямой API.
    Иначе — Grok ищет из открытых аналитических источников.
    """
    if not _token():
        # Fallback: ищем через Grok
        print(f"[Вова] MPStats токен не задан — ищу через Grok: {query}")
        result = _grok_marketplace(query)
        if result:
            return result + "\n\n🔵 **Вова** (данные из открытых отчётов · добавь MPSTATS_TOKEN для прямого API)"
        return "🔵 Вова: нет данных. Добавь MPSTATS_TOKEN в .env для прямого доступа к WB/Ozon."

    print(f"[Вова] Анализирую: {query}")
    parts = []

    # Определяем — это SKU (число) или категория/тема
    query_clean = query.strip()
    if query_clean.isdigit():
        # Анализ конкретного товара
        parts.append(wb_item(query_clean))
    else:
        # Подбираем категорию по теме
        category_map = {
            "снек": "Продукты питания/Снеки и чипсы",
            "протеин": "Спорт/Спортивное питание/Протеины и гейнеры",
            "батончик": "Спорт/Спортивное питание/Протеины и гейнеры",
            "йогурт": "Продукты питания/Молочные продукты",
            "напиток": "Продукты питания/Безалкогольные напитки",
            "чай": "Продукты питания/Чай и кофе/Чай",
            "кофе": "Продукты питания/Чай и кофе/Кофе",
            "витамин": "Красота/Витамины и БАДы",
            "бад": "Красота/Витамины и БАДы",
            "шоколад": "Продукты питания/Конфеты и шоколад",
            "печенье": "Продукты питания/Торты и десерты/Печенье",
        }

        category_wb = None
        q_lower = query_clean.lower()
        for keyword, path in category_map.items():
            if keyword in q_lower:
                category_wb = path
                break

        if not category_wb:
            # Пробуем использовать запрос напрямую как часть пути
            category_wb = f"Продукты питания/{query_clean}"

        # WB анализ
        wb_result = wb_category(category_wb)
        if wb_result:
            parts.append(wb_result)

        # Ключевые слова WB
        kw_result = wb_keywords(query_clean)
        if kw_result:
            parts.append("\n" + kw_result)

        # Ozon анализ (аналогичная категория)
        ozon_cat = category_wb.replace("Спорт/", "Спорт и отдых/").replace(
            "Продукты питания/", "Продукты/"
        )
        ozon_result = ozon_category(ozon_cat)
        if ozon_result and "нет данных" not in ozon_result:
            parts.append("\n" + ozon_result)

    if not parts:
        return f"Вова: не удалось получить данные по '{query}'"

    result = "\n".join(parts)
    result += "\n\n🔵 **Вова** (рыночный аналитик WB/Ozon · MPStats)"
    return result
