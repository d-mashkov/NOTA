"""
Агент Петя — компаратор трендов: Запад vs Россия.
Источники: Google Trends (pytrends) + Яндекс Suggest + Exa RU/EN.
"""

import os
import re
import requests
from dotenv import load_dotenv
from exa_py import Exa

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'), override=True)
_exa = Exa(api_key=os.getenv("EXA_API_KEY", ""))
_yandex_api_key = os.getenv("YANDEX_SEARCH_API_KEY", "")
_yandex_folder_id = os.getenv("YANDEX_FOLDER_ID", "")


def _google_trends(query: str) -> str:
    """Получает данные Google Trends: интерес по регионам и динамика."""
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="ru-RU", tz=180, timeout=(10, 30))
        pt.build_payload([query], timeframe="today 12-m", geo="")

        # Интерес по регионам
        by_region = pt.interest_by_region(resolution="COUNTRY", inc_low_vol=False)
        by_region = by_region.sort_values(query, ascending=False).head(10)

        # Динамика во времени
        over_time = pt.interest_over_time()

        lines = [f"📊 **Google Trends — «{query}»:**"]

        if not by_region.empty:
            lines.append("🌍 Топ стран по интересу:")
            for country, row in by_region.iterrows():
                val = int(row[query])
                if val > 0:
                    bar = "█" * (val // 10) + "░" * (10 - val // 10)
                    lines.append(f"  {country}: {bar} {val}/100")

        if not over_time.empty and query in over_time.columns:
            vals = over_time[query]
            avg_global = int(vals.mean())
            # Попробуем RU отдельно
            try:
                pt2 = TrendReq(hl="ru-RU", tz=180, timeout=(10, 30))
                pt2.build_payload([query], timeframe="today 12-m", geo="RU")
                ot_ru = pt2.interest_over_time()
                avg_ru = int(ot_ru[query].mean()) if not ot_ru.empty and query in ot_ru.columns else 0
                lines.append(f"\n📈 Средний интерес за 12 мес:")
                lines.append(f"  Глобально: {avg_global}/100")
                lines.append(f"  Россия: {avg_ru}/100")
                if avg_global > avg_ru + 20:
                    lines.append(f"  ⚡ Тренд опережает РФ на ~{avg_global - avg_ru} пунктов — потенциал входа!")
                elif avg_ru > avg_global:
                    lines.append(f"  🇷🇺 В РФ интерес выше глобального — рынок уже горячий.")
                else:
                    lines.append(f"  ≈ Уровень интереса в РФ соответствует глобальному.")
            except Exception:
                lines.append(f"\n📈 Глобальный интерес: {avg_global}/100")

        return "\n".join(lines)

    except Exception as e:
        print(f"[Петя] Google Trends error: {e}")
        return ""


def _exa_compare(query: str) -> str:
    """Сравнение через Exa: что пишут глобально vs в РФ."""
    try:
        # Глобальные материалы EN
        en_results = _exa.search_and_contents(
            f"{query} FMCG market trend consumer demand 2024 2025",
            num_results=4,
            text={"max_characters": 500},
        )
        # Российские материалы
        ru_results = _exa.search_and_contents(
            f"{query} рынок Россия тренд потребители 2024 2025",
            num_results=4,
            text={"max_characters": 500},
        )

        lines = []
        if en_results.results:
            lines.append("🌍 **Глобальный контекст:**")
            for r in en_results.results[:3]:
                lines.append(f"• {r.title or r.url}\n  {(r.text or '')[:250]}")

        if ru_results.results:
            lines.append("\n🇷🇺 **Россия:**")
            for r in ru_results.results[:3]:
                lines.append(f"• {r.title or r.url}\n  {(r.text or '')[:250]}")

        return "\n".join(lines)
    except Exception as e:
        print(f"[Петя] Exa error: {e}")
        return ""


def _yandex_search_ru(query: str) -> str:
    """Поиск через Yandex Search API v2 — реальные российские источники."""
    if not _yandex_api_key or not _yandex_folder_id:
        return ""
    try:
        import base64, xml.etree.ElementTree as ET
        r = requests.post(
            "https://searchapi.api.cloud.yandex.net/v2/web/search",
            headers={"Authorization": f"Api-Key {_yandex_api_key}", "Content-Type": "application/json"},
            json={
                "folderId": _yandex_folder_id,
                "query": {
                    "searchType": "SEARCH_TYPE_RU",
                    "queryText": query,
                    "maxPassages": 2,
                },
                "groupSpec": {"groupMode": "GROUP_MODE_DEEP", "groupsOnPage": 8, "docsInGroup": 1},
            },
            timeout=15,
        )
        if r.status_code != 200:
            return ""

        raw = r.json().get("rawData", "")
        xml_data = base64.b64decode(raw).decode("utf-8")
        root = ET.fromstring(xml_data)

        lines = [f"🇷🇺 **Яндекс поиск — «{query}»:**"]
        found = root.find(".//found-human")
        if found is not None:
            lines.append(f"  Найдено: {found.text}")

        for doc in root.findall(".//doc")[:6]:
            title = doc.findtext("title") or ""
            url = doc.findtext("url") or ""
            passage = doc.findtext(".//passage") or ""
            # Убираем XML-теги из title
            title_clean = ET.tostring(doc.find("title"), encoding="unicode", method="text") if doc.find("title") is not None else title
            if title_clean and url:
                lines.append(f"  • {title_clean[:80]}")
                if passage:
                    lines.append(f"    {passage[:150]}")

        return "\n".join(lines)
    except Exception as e:
        print(f"[Петя] Yandex Search error: {e}")
        return ""


def _yandex_suggest(query: str) -> str:
    """Яндекс Suggest — что люди ищут в Яндексе по теме."""
    try:
        r = requests.get(
            "http://suggest.yandex.ru/suggest-ya.cgi",
            params={"part": query, "uil": "ru", "n": 10},
            timeout=8,
        )
        text = r.text
        # Парсим массив подсказок из ответа
        match = re.search(r'\["[^"]*",(\[.*?\])\]', text)
        if not match:
            return ""
        suggestions_str = match.group(1)
        suggestions = re.findall(r'"([^"]+)"', suggestions_str)
        if not suggestions:
            return ""

        lines = [f"🔍 **Яндекс — что ищут люди по теме «{query}»:**"]
        for s in suggestions[:8]:
            lines.append(f"  • {s}")
        lines.append(f"\n💡 Таких подсказок {len(suggestions)} — это реальные запросы пользователей Яндекса.")
        return "\n".join(lines)
    except Exception as e:
        print(f"[Петя] Yandex Suggest error: {e}")
        return ""


def compare_trends_global_vs_russia(query: str) -> str:
    """
    Сравнивает тренд глобально и в России.
    Google Trends + Exa RU/EN.
    """
    print(f"[Петя] Сравнение трендов: {query}")
    parts = []

    # 1. Яндекс Search API — реальные российские результаты
    yandex_search = _yandex_search_ru(f"{query} рынок Россия тренд спрос")
    if yandex_search:
        parts.append(yandex_search)

    # 2. Яндекс Suggest — что ищут люди
    yandex = _yandex_suggest(query)
    if yandex:
        parts.append("\n" + yandex)

    # 2. Google Trends — глобал vs РФ
    trends = _google_trends(query)
    if trends:
        parts.append("\n" + trends)

    # 3. Exa RU/EN — контекст рынка
    exa = _exa_compare(query)
    if exa:
        parts.append("\n" + exa)

    if not parts:
        return "Петя: данных по запросу не найдено."

    return "\n".join(parts)
