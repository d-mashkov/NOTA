"""
Агент Авоська — FMCG гений.
Парсит экспортированные Telegram-каналы по FMCG,
анализирует через Claude, выявляет топ-10 инсайтов.
Сохраняет в Supabase таблицу trend_signals.
"""

import os
import re
import json
import requests
import anthropic
from datetime import datetime, date
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'), override=True)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    return _client

# Пути к экспортам Telegram
TG_EXPORT_FILES = [
    "/Users/denismaskov/Downloads/Telegram Desktop/ChatExport_2026-06-07/messages.html",
    "/Users/denismaskov/Downloads/Telegram Desktop/ChatExport_2026-06-07/messages2.html",
    "/Users/denismaskov/Downloads/Telegram Desktop/ChatExport_2026-06-07/messages3.html",
    "/Users/denismaskov/Downloads/Telegram Desktop/ChatExport_2026-06-08/messagesNtech.html",
]


def _parse_tg_exports() -> list[dict]:
    """Парсит HTML-экспорты Telegram каналов."""
    all_msgs = []
    for fpath in TG_EXPORT_FILES:
        if not os.path.exists(fpath):
            continue
        try:
            soup = BeautifulSoup(open(fpath, encoding='utf-8'), 'html.parser')
            title_div = soup.find('div', class_='text bold')
            channel = title_div.get_text(strip=True) if title_div else os.path.basename(fpath)
            msgs = soup.find_all('div', class_='message default clearfix')
            for m in msgs:
                text_div = m.find('div', class_='text')
                date_div = m.find('div', class_='date details')
                if not text_div:
                    continue
                text = text_div.get_text(' ', strip=True)
                if len(text) < 30:
                    continue
                date_str = date_div.get('title', '')[:10] if date_div else ''
                links = [
                    a['href'] for a in text_div.find_all('a', href=True)
                    if a.get('href', '').startswith('http') and 't.me' not in a['href']
                ][:3]
                all_msgs.append({
                    'channel': channel,
                    'text': text[:800],
                    'date': date_str,
                    'links': links,
                })
        except Exception as e:
            print(f"[Авоська] Ошибка парсинга {fpath}: {e}")
    return all_msgs


def _fetch_link_content(url: str) -> str:
    """Получает текст по ссылке из сообщения."""
    try:
        r = requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.text, 'html.parser')
        # Убираем скрипты и стили
        for tag in soup(['script', 'style', 'nav', 'footer']):
            tag.decompose()
        text = soup.get_text(' ', strip=True)
        return text[:1500]
    except Exception:
        return ""


def _grok_fmcg_insights(query: str) -> str:
    """Fallback через Grok когда в TG каналах нет данных по теме."""
    key = os.getenv("GROK_API_KEY", "")
    if not key:
        return f"Авоська: в Telegram каналах нет данных по теме «{query}»."
    try:
        r = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "grok-4.3",
                "tools": [{"type": "web_search"}],
                "input": [{"role": "user", "content": (
                    f"Найди свежие профессиональные инсайты и аналитику по теме: {query}\n\n"
                    f"Контекст: российский FMCG рынок, запуск нового продукта.\n\n"
                    f"Ответь строго на русском языке. Простые абзацы, без таблиц.\n\n"
                    f"Напиши:\n"
                    f"1. Что говорят отраслевые эксперты и аналитики об этой нише\n"
                    f"2. Какие бренды и продукты активно обсуждают в профессиональном сообществе\n"
                    f"3. Какие тренды и инсайты важны для запуска в России\n"
                    f"4. Конкретный вывод — стоит ли входить сейчас\n\n"
                    f"Максимум 250 слов."
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
        result = "\n".join(parts).strip()
        return result + "\n\n🛒 Авоська (поиск по открытым FMCG источникам)" if result else f"Авоська: нет данных по теме «{query}»."
    except Exception as e:
        print(f"[Авоська] Grok fallback error: {e}")
        return f"Авоська: нет данных по теме «{query}»."


def analyze_tg_channels(query: str = "") -> str:
    """
    Главная функция Авоськи:
    1. Парсит все Telegram экспорты
    2. Фильтрует по теме если задан query
    3. Анализирует через Claude
    4. Возвращает топ инсайтов
    """
    print(f"[Авоська] Анализирую Telegram каналы... query={query or 'все'}")
    msgs = _parse_tg_exports()
    print(f"[Авоська] Загружено {len(msgs)} сообщений из {len(TG_EXPORT_FILES)} каналов")

    if not msgs:
        return "Авоська: экспорты Telegram не найдены."

    # Фильтруем по теме если нужно
    if query:
        q_lower = query.lower()
        # Разбиваем запрос на ключевые слова, ищем хотя бы одно вхождение
        keywords = [w for w in q_lower.replace('—', ' ').split() if len(w) > 3]
        filtered = [m for m in msgs if any(kw in m['text'].lower() for kw in keywords)]
        if filtered:
            msgs = filtered
            print(f"[Авоська] По теме '{query}': {len(msgs)} сообщений")
        else:
            # Нет релевантных сообщений — возвращаем это явно через Grok
            print(f"[Авоська] По теме '{query}' в TG каналах ничего нет — fallback Grok")
            return _grok_fmcg_insights(query)

    # Берём последние 150 сообщений (самые свежие)
    msgs_sample = msgs[-150:] if len(msgs) > 150 else msgs

    # Подтягиваем контент по важным ссылкам (топ-5)
    link_contents = []
    links_checked = 0
    for m in msgs_sample:
        for link in m.get('links', []):
            if links_checked >= 5:
                break
            content = _fetch_link_content(link)
            if content:
                link_contents.append(f"URL: {link}\n{content[:600]}")
                links_checked += 1
        if links_checked >= 5:
            break

    # Формируем контекст для Claude
    msgs_text = "\n\n".join([
        f"[{m['channel']} | {m['date']}]\n{m['text']}"
        for m in msgs_sample
    ])

    links_text = "\n\n---\n\n".join(link_contents) if link_contents else "Нет доступных ссылок."

    prompt_focus = f"Особое внимание удели теме: {query}" if query else "Анализируй все темы."

    prompt = f"""Ты — Авоська, FMCG гений и эксперт по российскому рынку потребительских товаров.

Тебе предоставлены сообщения из профессиональных FMCG Telegram-каналов за последние недели.
{prompt_focus}

СООБЩЕНИЯ ИЗ TELEGRAM КАНАЛОВ:
{msgs_text[:6000]}

КОНТЕНТ ПО ССЫЛКАМ ИЗ СООБЩЕНИЙ:
{links_text[:2000]}

Твоя задача:
1. Найди 5-7 самых интересных и actionable инсайтов для FMCG предпринимателя в России
2. Для каждого инсайта укажи:
   - О чём это (кратко, 1 строка)
   - Почему важно (2-3 строки)
   - Что это значит для запуска нового продукта
3. Выдели тренды, которые можно монетизировать

Формат ответа — Markdown для Telegram.
В конце подпиши: 🛒 **Авоська (FMCG гений)** — проанализировал {len(msgs_sample)} сообщений из каналов."""

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def get_weekly_insights() -> list[dict]:
    """
    Генерирует топ-5 инсайтов недели для сайта NOTA.
    Возвращает список из 5 словарей для сохранения в Supabase.
    """
    print("[Авоська] Генерирую еженедельные инсайты для сайта...")
    msgs = _parse_tg_exports()
    if not msgs:
        return []

    msgs_sample = msgs[-200:] if len(msgs) > 200 else msgs
    msgs_text = "\n\n".join([
        f"[{m['channel']} | {m['date']}]\n{m['text']}"
        for m in msgs_sample
    ])

    prompt = f"""Ты — Авоська, FMCG гений. Анализируй сообщения из профессиональных FMCG каналов.

СООБЩЕНИЯ:
{msgs_text[:8000]}

Выдели ровно 5 САМЫХ ЯРКИХ инсайтов с конкретными цифрами, процентами и фактами.
ВАЖНО: каждый инсайт ОБЯЗАН содержать цифры — рост в %, объём рынка в рублях, динамику продаж и т.д.
Если в сообщениях нет цифр по теме — не включай её.

Для каждого верни JSON-объект:
{{
  "title": "Заголовок с главной цифрой, до 8 слов (пример: 'Йогурты +182% — рекорд года')",
  "summary": "2-3 предложения с конкретными данными: цифры роста, объём, сравнения, источник данных. Пиши что означает для предпринимателя.",
  "stat": "Главная цифра/факт одной строкой (например: '+182% в деньгах, +67% в штуках')",
  "category": "одно из: тренд | рынок | продукт | ритейл | потребитель | регулирование",
  "importance": "высокая | средняя",
  "source_channel": "название канала"
}}

Верни ТОЛЬКО валидный JSON массив из 5 объектов. Никакого другого текста."""

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Убираем markdown-обёртку если есть
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    insights = json.loads(raw)
    today = date.today().isoformat()
    for ins in insights:
        ins['date'] = today
        ins['agent'] = 'Авоська'
    return insights
