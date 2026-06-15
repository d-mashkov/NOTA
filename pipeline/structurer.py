"""
Converts raw agent text → typed JSON structs.
Uses claude-haiku-4-5 (fast + cheap) for extraction.
Computes the final idea score from 5 weighted sub-scores.
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'), override=True)

# ── Schemas sent to Claude as "return this JSON" ──────────────────────────────

SCHEMAS = {
    "artem": {
        "trend_strength": "integer 0-100 — насколько сильны социальные сигналы",
        "sentiment": "positive | neutral | negative",
        "key_signals": ["список 3-5 конкретных сигналов из данных — цифры, посты, названия"],
        "verdict": "1 предложение — есть ли реальный тренд"
    },
    "petya": {
        "search_demand_ru": "integer 0-100 — относительная сила спроса в Яндексе/Google по РФ",
        "top_queries": ["список 3-5 реальных поисковых запросов из данных"],
        "trend_direction": "growing | stable | declining",
        "verdict": "1 предложение — что говорит поисковый спрос"
    },
    "vova": {
        "market_activity": "integer 0-100 — насколько активна ниша на WB/Ozon",
        "competition_density": "low | medium | high",
        "avg_price_range": "строка вида '500-1500 ₽' или '—' если нет данных",
        "top_sellers": ["список 2-4 реальных брендов/продавцов из данных или [] если нет"],
        "verdict": "1 предложение — что показывают маркетплейсы"
    },
    "avoska": {
        "industry_buzz": "integer 0-100 — насколько тема горячая в профессиональном сообществе",
        "key_insights": ["список 2-4 конкретных инсайта из данных"],
        "monetization_signal": "high | medium | low",
        "verdict": "1 предложение — что говорит отраслевое сообщество"
    },
    "polya": {
        "gtm_clarity": "integer 0-100 — насколько понятен путь выхода на рынок",
        "top_channels": ["список 2-4 каналов дистрибуции для РФ"],
        "time_to_market": "строка вида '3-6 месяцев'",
        "positioning": "1 предложение — суть позиционирования",
        "verdict": "1 предложение — готовность к запуску"
    }
}

FALLBACKS = {
    "artem":  {"trend_strength": 50, "sentiment": "neutral", "key_signals": [], "verdict": "Данные ограничены."},
    "petya":  {"search_demand_ru": 50, "top_queries": [], "trend_direction": "stable", "verdict": "Данные ограничены."},
    "vova":   {"market_activity": 50, "competition_density": "medium", "avg_price_range": "—", "top_sellers": [], "verdict": "Данные ограничены."},
    "avoska": {"industry_buzz": 50, "key_insights": [], "monetization_signal": "medium", "verdict": "Данные ограничены."},
    "polya":  {"gtm_clarity": 50, "top_channels": [], "time_to_market": "—", "positioning": "—", "verdict": "Данные ограничены."},
}


def structure_agent_output(agent_name: str, raw_text: str, idea_title: str) -> dict:
    """
    Вызывает Claude Haiku и извлекает типизированный JSON из сырого текста агента.
    При ошибке возвращает FALLBACKS[agent_name].
    """
    if not raw_text or len(raw_text.strip()) < 20:
        return FALLBACKS[agent_name]

    schema = SCHEMAS[agent_name]
    prompt = (
        f"Идея: {idea_title}\n\n"
        f"Сырые данные агента ({agent_name}):\n{raw_text[:2000]}\n\n"
        f"Извлеки ТОЛЬКО факты из текста выше. Не придумывай данные.\n"
        f"Если данных по полю нет — используй значение по умолчанию из схемы.\n\n"
        f"Верни JSON строго по схеме (без markdown, только JSON):\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}"
    )

    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        # Гарантируем наличие всех ключей
        for key, default in FALLBACKS[agent_name].items():
            if key not in result:
                result[key] = default
        return result
    except Exception as e:
        print(f"[Structurer] Ошибка структурирования {agent_name}: {e}")
        return FALLBACKS[agent_name]


# ── Score rubric ──────────────────────────────────────────────────────────────
#
#   demand      (25%) — социальный сигнал (Артём) + поисковый спрос (Петя)
#   market      (25%) — активность ниши на WB/Ozon (Вова)
#   competition (20%) — обратная плотность конкуренции — меньше конкурентов = выше балл
#   trend       (15%) — направление тренда (Петя) + отраслевой buzz (Авоська)
#   gtm         (15%) — ясность пути на рынок (Поля)

_COMPETITION_MAP = {"low": 85, "medium": 55, "high": 25}
_DIRECTION_MAP   = {"growing": 85, "stable": 55, "declining": 20}
_MONETIZE_MAP    = {"high": 85, "medium": 55, "low": 25}


def compute_score(structs: dict) -> tuple:
    """
    structs = {"artem": {...}, "petya": {...}, "vova": {...}, "avoska": {...}, "polya": {...}}
    Возвращает (final_score: int, sub_scores: dict)
    """
    a  = structs.get("artem",  FALLBACKS["artem"])
    p  = structs.get("petya",  FALLBACKS["petya"])
    v  = structs.get("vova",   FALLBACKS["vova"])
    av = structs.get("avoska", FALLBACKS["avoska"])
    po = structs.get("polya",  FALLBACKS["polya"])

    demand      = round(a.get("trend_strength", 50) * 0.5 + p.get("search_demand_ru", 50) * 0.5)
    market      = v.get("market_activity", 50)
    competition = _COMPETITION_MAP.get(v.get("competition_density", "medium"), 55)
    trend       = round(
        _DIRECTION_MAP.get(p.get("trend_direction", "stable"), 55) * 0.6
        + _MONETIZE_MAP.get(av.get("monetization_signal", "medium"), 55) * 0.4
    )
    gtm = po.get("gtm_clarity", 50)

    sub_scores = {
        "demand":      min(100, max(0, int(demand))),
        "market":      min(100, max(0, int(market))),
        "competition": min(100, max(0, int(competition))),
        "trend":       min(100, max(0, int(trend))),
        "gtm":         min(100, max(0, int(gtm))),
    }

    final = round(
        sub_scores["demand"]      * 0.25
        + sub_scores["market"]      * 0.25
        + sub_scores["competition"] * 0.20
        + sub_scores["trend"]       * 0.15
        + sub_scores["gtm"]         * 0.15
    )

    return min(100, max(0, final)), sub_scores
