# Structured Agent Output + Score Rubric — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each agent returns a typed JSON struct instead of raw text; the final idea score is computed from 5 explicit sub-scores with defined weights instead of being guessed by Claude.

**Architecture:** A new `pipeline/structurer.py` module wraps every agent's raw text output with a fast Claude Haiku call that extracts a typed schema. `run_launch_ideas.py` imports `structure_agent_output` and `compute_score`, uses structured data to fill the synthesis prompt, stores sub-scores in `detail_json`. `idea-detail.html` renders a sub-score bar chart instead of (or alongside) the existing donut.

**Tech Stack:** Python 3.9, `anthropic` SDK (claude-haiku-4-5 for structuring, claude-sonnet-4-5 for synthesis), Supabase `launch_ideas.detail_json` TEXT column, Chart.js 4.4.0 (already loaded), vanilla JS.

---

## File map

| File | Action | What changes |
|------|--------|--------------|
| `pipeline/structurer.py` | **Create** | `structure_agent_output()`, `compute_score()`, typed schemas |
| `pipeline/run_launch_ideas.py` | **Modify** | import structurer, call it after each agent, use sub-scores |
| `idea-detail.html` | **Modify** | read `detail.sub_scores`, render horizontal sub-score bars |

---

## Task 1 — Create `pipeline/structurer.py`

**Files:**
- Create: `pipeline/structurer.py`

This module has two responsibilities:
1. `structure_agent_output(agent_name, raw_text, idea_title)` — calls Claude Haiku to extract a typed JSON struct from an agent's raw text
2. `compute_score(structs)` — applies the weighted rubric and returns `(final_score, sub_scores_dict)`

- [ ] **Step 1: Create the file with schemas and `structure_agent_output`**

```python
# pipeline/structurer.py
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
        # Убираем markdown-обёртку если есть
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        # Гарантируем наличие всех ключей
        fallback = FALLBACKS[agent_name]
        for key, default in fallback.items():
            if key not in result:
                result[key] = default
        return result
    except Exception as e:
        print(f"[Structurer] Ошибка структурирования {agent_name}: {e}")
        return FALLBACKS[agent_name]
```

- [ ] **Step 2: Add `compute_score` to the same file**

Append to `pipeline/structurer.py`:

```python

# ── Score rubric ──────────────────────────────────────────────────────────────
#
# Итоговый балл = взвешенная сумма 5 субоценок:
#
#   demand      (25%) — социальный сигнал (Артём) + поисковый спрос (Петя)
#   market      (25%) — активность ниши на WB/Ozon (Вова)
#   competition (20%) — обратная плотность конкуренции (Вова) — меньше конкурентов = выше балл
#   trend       (15%) — направление тренда (Петя) + отраслевой buzz (Авоська)
#   gtm         (15%) — ясность пути на рынок (Поля)

_COMPETITION_MAP = {"low": 85, "medium": 55, "high": 25}
_DIRECTION_MAP   = {"growing": 85, "stable": 55, "declining": 20}
_MONETIZE_MAP    = {"high": 85, "medium": 55, "low": 25}


def compute_score(structs: dict) -> tuple[int, dict]:
    """
    structs = {"artem": {...}, "petya": {...}, "vova": {...}, "avoska": {...}, "polya": {...}}

    Возвращает (final_score: int, sub_scores: dict)
    sub_scores = {"demand": int, "market": int, "competition": int, "trend": int, "gtm": int}
    """
    a = structs.get("artem",  FALLBACKS["artem"])
    p = structs.get("petya",  FALLBACKS["petya"])
    v = structs.get("vova",   FALLBACKS["vova"])
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
        "demand":      min(100, max(0, demand)),
        "market":      min(100, max(0, market)),
        "competition": min(100, max(0, competition)),
        "trend":       min(100, max(0, trend)),
        "gtm":         min(100, max(0, gtm)),
    }

    final = round(
        sub_scores["demand"]      * 0.25
        + sub_scores["market"]      * 0.25
        + sub_scores["competition"] * 0.20
        + sub_scores["trend"]       * 0.15
        + sub_scores["gtm"]         * 0.15
    )

    return min(100, max(0, final)), sub_scores
```

- [ ] **Step 3: Smoke-test the module**

```bash
cd /Users/denismaskov/nota
python3 -c "
from pipeline.structurer import structure_agent_output, compute_score, FALLBACKS

# Test structurer с реальным текстом
raw = 'TikTok тренды: патчи для кожи набирают 2M просмотров в неделю. Reddit: 1200 постов за месяц с позитивным тоном. Grok: растущий интерес, тональность позитивная.'
result = structure_agent_output('artem', raw, 'Патчи для кожи')
print('artem struct:', result)
assert 'trend_strength' in result
assert isinstance(result['trend_strength'], int)

# Test compute_score
structs = {k: FALLBACKS[k] for k in FALLBACKS}
structs['artem']['trend_strength'] = 80
structs['petya']['search_demand_ru'] = 70
structs['vova']['competition_density'] = 'low'
score, subs = compute_score(structs)
print('score:', score, 'subs:', subs)
assert 60 < score < 90, f'Expected 60-90, got {score}'
print('OK')
"
```

Expected output:
```
artem struct: {'trend_strength': <int>, 'sentiment': '...', 'key_signals': [...], 'verdict': '...'}
score: <int between 60-90>  subs: {'demand': ..., 'market': ..., ...}
OK
```

- [ ] **Step 4: Commit**

```bash
cd /Users/denismaskov/nota
git add pipeline/structurer.py
git commit -m "feat: add agent structurer + score rubric with 5 weighted sub-scores"
```

---

## Task 2 — Wire structurer into `run_launch_ideas.py`

**Files:**
- Modify: `pipeline/run_launch_ideas.py` — lines 1-15 (imports), `generate_idea()` function

- [ ] **Step 1: Add import at the top of `run_launch_ideas.py`**

Find the block:
```python
from pipeline.agents.artem import search_social_trends
```

Replace the entire imports block with:
```python
from pipeline.agents.artem import search_social_trends
from pipeline.agents.petya import compare_trends_global_vs_russia
from pipeline.agents.vova import analyze_marketplace
from pipeline.agents.avoska import analyze_tg_channels
from pipeline.agents.polya import build_marketing_strategy
from pipeline.supabase_client import supabase
from pipeline.structurer import structure_agent_output, compute_score
```

- [ ] **Step 2: Replace `generate_idea()` body — agent calls + structuring**

Find the block starting with `print(f"[Ideas] → Артём ищет тренды...")` through `polya = build_marketing_strategy(...)`.

Replace with:

```python
    print(f"[Ideas] → Артём ищет тренды...")
    artem_raw = search_social_trends(query)

    print(f"[Ideas] → Петя анализирует SEO...")
    petya_raw = compare_trends_global_vs_russia(query)

    print(f"[Ideas] → Вова смотрит маркетплейсы...")
    vova_raw = analyze_marketplace(title)

    print(f"[Ideas] → Авоська читает каналы...")
    avoska_raw = analyze_tg_channels(title)

    print(f"[Ideas] → Поля строит стратегию...")
    polya_raw = build_marketing_strategy(title, context=f"{artem_raw[:300]}\n{petya_raw[:300]}\n{vova_raw[:300]}")

    # Структурируем вывод каждого агента
    print(f"[Ideas] → Структурируем данные агентов...")
    structs = {
        "artem":  structure_agent_output("artem",  artem_raw,  title),
        "petya":  structure_agent_output("petya",  petya_raw,  title),
        "vova":   structure_agent_output("vova",   vova_raw,   title),
        "avoska": structure_agent_output("avoska", avoska_raw, title),
        "polya":  structure_agent_output("polya",  polya_raw,  title),
    }

    # Считаем балл по рубрике
    computed_score, sub_scores = compute_score(structs)
    print(f"[Ideas] Субскоры: {sub_scores} → итог: {computed_score}")
```

- [ ] **Step 3: Update the synthesis prompt to use structured verdicts**

Find:
```python
    synthesis_prompt = f"""Ты — главный аналитик NOTA. Оцени идею запуска продукта в России на основе данных от агентов.

ВАЖНО: все твои выводы должны касаться ТОЛЬКО этой конкретной идеи. Не смешивай данные разных категорий.

Идея: {title}
Группа: {group}

Данные агентов:
🔴 Артём (соцсети/тренды): {artem[:700]}
🟡 Петя (SEO/поиск): {petya[:700]}
🔵 Вова (маркетплейсы WB/Ozon): {vova[:700]}
🛒 Авоська (FMCG Telegram-каналы): {avoska[:700]}
🟣 Поля (маркетинг/GTM): {polya[:700]}
```

Replace with:

```python
    # Готовим компактные вердикты из структур для синтез-промпта
    agent_verdicts = "\n".join([
        f"🔴 Артём (тренды, сила {structs['artem']['trend_strength']}/100): {structs['artem']['verdict']}",
        f"   Сигналы: {', '.join(structs['artem']['key_signals'][:3])}",
        f"🟡 Петя (спрос РФ {structs['petya']['search_demand_ru']}/100, {structs['petya']['trend_direction']}): {structs['petya']['verdict']}",
        f"   Запросы: {', '.join(structs['petya']['top_queries'][:3])}",
        f"🔵 Вова (активность {structs['vova']['market_activity']}/100, конкуренция: {structs['vova']['competition_density']}): {structs['vova']['verdict']}",
        f"   Топ продавцы: {', '.join(structs['vova']['top_sellers'][:3]) or '—'}",
        f"🛒 Авоська (buzz {structs['avoska']['industry_buzz']}/100): {structs['avoska']['verdict']}",
        f"   Инсайты: {'; '.join(structs['avoska']['key_insights'][:2])}",
        f"🟣 Поля (GTM {structs['polya']['gtm_clarity']}/100): {structs['polya']['verdict']}",
        f"   Каналы: {', '.join(structs['polya']['top_channels'][:3])}  Срок: {structs['polya']['time_to_market']}",
    ])

    synthesis_prompt = f"""Ты — главный аналитик NOTA. Составь итоговую карточку идеи на основе структурированных данных агентов.

ВАЖНО: только про эту идею. Балл уже рассчитан по рубрике — используй {computed_score} как основу, можешь скорректировать ±5 если видишь важные факторы.

Идея: {title}
Группа: {group}
Рассчитанный балл: {computed_score}/100

Вердикты агентов:
{agent_verdicts}

Полные данные для market_size / growth_rate / key_players / entry_price:
{vova_raw[:600]}
{petya_raw[:400]}
```

- [ ] **Step 4: Update return value and `detail_json` to include sub_scores and structs**

Find:
```python
    # detail_json — всё что нужно для страницы детей
    detail_json = {
        "market_size": data.get("market_size", ""),
```

Replace the entire `detail_json` dict and the `return` statement below it:

```python
    # detail_json — всё что нужно для страницы детали
    detail_json = {
        "market_size":     data.get("market_size", ""),
        "growth_rate":     data.get("growth_rate", ""),
        "key_players":     data.get("key_players", []),
        "entry_price":     data.get("entry_price", ""),
        "packaging_ideas": data.get("packaging_ideas", []),
        "launch_steps":    data.get("launch_steps", []),
        "risks":           data.get("risks", []),
        "sources":         data.get("sources", []),
        "group":           group,
        # Субскоры рубрики
        "sub_scores": sub_scores,
        # Структурированные данные агентов (для будущих фич)
        "structs": structs,
        # Полные тексты агентов
        "artem_full":  artem_raw,
        "petya_full":  petya_raw,
        "vova_full":   vova_raw,
        "avoska_full": avoska_raw,
        "polya_full":  polya_raw,
    }

    # Балл: берём computed_score, Claude может скорректировать ±5
    final_score = data.get("score", computed_score)
    # Ограничиваем корректировку Клода диапазоном ±8
    final_score = max(computed_score - 8, min(computed_score + 8, int(final_score)))

    return {
        "title":    title,
        "category": data.get("category", group),
        "summary":  data.get("summary", ""),
        "score":    final_score,
        "artem":  f"{structs['artem']['verdict']}\n\n{artem_raw[:800]}",
        "petya":  f"{structs['petya']['verdict']}\n\n{petya_raw[:800]}",
        "vova":   f"{structs['vova']['verdict']}\n\n{vova_raw[:800]}",
        "avoska": f"{structs['avoska']['verdict']}\n\n{avoska_raw[:800]}",
        "polya":  f"{structs['polya']['verdict']}\n\n{polya_raw[:800]}",
        "detail_json": json.dumps(detail_json, ensure_ascii=False),
        "status": "active",
    }
```

- [ ] **Step 5: Also update the fallback `data` dict (when synthesis fails) to use `computed_score`**

Find:
```python
    except Exception as e:
        print(f"[Ideas] Ошибка синтеза: {e}")
        data = {
            "summary": "Перспективная ниша для запуска на российском рынке.",
            "score": 65,
```

Replace:
```python
    except Exception as e:
        print(f"[Ideas] Ошибка синтеза: {e}")
        data = {
            "summary": "Перспективная ниша для запуска на российском рынке.",
            "score": computed_score,
```

- [ ] **Step 6: Quick smoke-test — dry run one seed**

```bash
cd /Users/denismaskov/nota
python3 -c "
import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env', override=True)

# Тестируем только structurer + compute_score без вызова агентов
from pipeline.structurer import structure_agent_output, compute_score

fake_artem = 'TikTok: протеиновые снеки набирают 5M просмотров. Reddit: 800 постов, тональность позитивная. X/Twitter: рост обсуждений +40% за квартал.'
fake_petya = 'Яндекс: 450 000 запросов/мес по теме протеиновые снеки. Тренд растущий. Google Trends: RU опережает глобал на 15 пунктов.'
fake_vova  = 'WB: категория снеки 2.1 млрд руб/мес. Топ бренды: Chikalab, Bombbar. Конкуренция высокая. Средняя цена 150-350 руб.'
fake_av    = 'В FMCG каналах активно обсуждают: рост продаж протеин-снеков +60% г/г. Крупные сети вводят СТМ в этой категории.'
fake_polya = 'GTM: WB/Ozon главные каналы (70%), Instagram инфлюенсеры-нутрициологи. Срок выхода 4-6 мес. Позиционирование: вкусный протеин без компромиссов.'

structs = {
    'artem':  structure_agent_output('artem',  fake_artem, 'Протеиновые снеки'),
    'petya':  structure_agent_output('petya',  fake_petya, 'Протеиновые снеки'),
    'vova':   structure_agent_output('vova',   fake_vova,  'Протеиновые снеки'),
    'avoska': structure_agent_output('avoska', fake_av,    'Протеиновые снеки'),
    'polya':  structure_agent_output('polya',  fake_polya, 'Протеиновые снеки'),
}
score, subs = compute_score(structs)
print('Субскоры:', subs)
print('Итог:', score)
for k, v in structs.items():
    print(f'{k}: verdict={v[\"verdict\"][:60]}')
"
```

Expected: все 5 агентов вернули структуры без ошибок, итоговый score распечатан.

- [ ] **Step 7: Commit**

```bash
cd /Users/denismaskov/nota
git add pipeline/run_launch_ideas.py
git commit -m "feat: wire structurer into generate_idea, score from rubric not Claude guess"
```

---

## Task 3 — Sub-score bars in `idea-detail.html`

**Files:**
- Modify: `idea-detail.html` — CSS block + metrics HTML block + JS `init()` function

The sub-score bars replace the "Рыночные метрики" row. The 4 metric boxes (market_size, growth_rate, entry_price, players) stay below.

- [ ] **Step 1: Add CSS for sub-score bars**

In `idea-detail.html`, find the end of the `<style>` block (just before `</style>`), and append:

```css
    /* ── Субскоры ── */
    .sub-scores {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 16px;
    }
    .sub-score-row {
      display: grid;
      grid-template-columns: 110px 1fr 36px;
      align-items: center;
      gap: 10px;
    }
    .sub-score-label {
      font-size: 11px; font-weight: 600; color: var(--text-muted);
      text-transform: uppercase; letter-spacing: 0.06em;
    }
    .sub-score-track {
      height: 6px;
      background: rgba(255,255,255,0.07);
      border-radius: 3px;
      overflow: hidden;
    }
    .sub-score-fill {
      height: 100%;
      border-radius: 3px;
      transition: width 0.7s ease;
    }
    .sub-score-fill.high  { background: var(--green);  box-shadow: 0 0 8px rgba(16,185,129,0.5); }
    .sub-score-fill.mid   { background: var(--yellow); box-shadow: 0 0 8px rgba(245,158,11,0.5); }
    .sub-score-fill.low   { background: var(--red);    box-shadow: 0 0 8px rgba(239,68,68,0.5); }
    .sub-score-val {
      font-size: 12px; font-weight: 700; text-align: right;
    }
    .sub-score-val.high  { color: var(--green); }
    .sub-score-val.mid   { color: var(--yellow); }
    .sub-score-val.low   { color: var(--red); }
```

- [ ] **Step 2: Add sub-scores HTML block to the page**

Find:
```html
    <!-- Метрики -->
    <div class="d-block full" style="margin-bottom:16px;">
      <div class="d-block-title"><span>📊</span> Рыночные метрики</div>
      <div class="metrics-row">
```

Replace the entire block (through the closing `</div>` of `d-block full`) with:

```html
    <!-- Субскоры балла -->
    <div class="d-block full" style="margin-bottom:16px;">
      <div class="d-block-title"><span>📊</span> Из чего складывается балл</div>
      <div class="sub-scores" id="sub-scores">
        <!-- заполняется JS -->
      </div>
    </div>

    <!-- Рыночные метрики -->
    <div class="d-block full" style="margin-bottom:16px;">
      <div class="d-block-title"><span>🏪</span> Рыночные метрики</div>
      <div class="metrics-row">
        <div class="metric-box">
          <div class="metric-label">Объём рынка РФ</div>
          <div class="metric-value" id="m-size">—</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Темп роста</div>
          <div class="metric-value" id="m-growth">—</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Цена входа</div>
          <div class="metric-value" id="m-price">—</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Ключевые игроки</div>
          <div class="players-row" id="m-players" style="margin-top:4px;"></div>
        </div>
      </div>
    </div>
```

- [ ] **Step 3: Add `renderSubScores()` JS function**

In `idea-detail.html`, find `function sc(s)` in the `<script>` block and add **before** it:

```js
    const SUB_SCORE_LABELS = {
      demand:      "Спрос",
      market:      "Рынок РФ",
      competition: "Конкуренция",
      trend:       "Тренд",
      gtm:         "Выход на рынок",
    };
    const SUB_SCORE_WEIGHTS = {
      demand: "25%", market: "25%", competition: "20%", trend: "15%", gtm: "15%"
    };

    function renderSubScores(subScores) {
      const container = document.getElementById('sub-scores');
      if (!subScores || !Object.keys(subScores).length) {
        container.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">Субскоры появятся при следующей генерации</div>';
        return;
      }
      container.innerHTML = Object.entries(subScores).map(([key, val]) => {
        const cls = val >= 70 ? 'high' : val >= 45 ? 'mid' : 'low';
        const label = SUB_SCORE_LABELS[key] || key;
        const weight = SUB_SCORE_WEIGHTS[key] || '';
        return `
          <div class="sub-score-row">
            <div class="sub-score-label" title="вес ${weight}">${label} <span style="opacity:.5;font-size:9px">${weight}</span></div>
            <div class="sub-score-track">
              <div class="sub-score-fill ${cls}" style="width:${val}%"></div>
            </div>
            <div class="sub-score-val ${cls}">${val}</div>
          </div>`;
      }).join('');
    }
```

- [ ] **Step 4: Call `renderSubScores` in `init()`**

Find this line in `init()`:
```js
      // Metrics
      document.getElementById('m-size').textContent = detail.market_size || '—';
```

Add **one line before** it:
```js
      // Sub-scores
      renderSubScores(detail.sub_scores || {});

      // Metrics
      document.getElementById('m-size').textContent = detail.market_size || '—';
```

- [ ] **Step 5: Verify in browser**

```bash
# Убедись что сервер запущен
lsof -i :3000 | grep LISTEN
# Если нет:
cd /Users/denismaskov/nota && python3 -m http.server 3000 &
```

Открой `http://localhost:3000/idea-detail.html?id=<любой_id>`.

Для идей сгенерированных до этого апдейта: `detail.sub_scores` будет `{}` → покажется заглушка.  
Для новых идей (после следующего запуска пайплайна): покажутся 5 строк с цветными барами.

- [ ] **Step 6: Commit**

```bash
cd /Users/denismaskov/nota
git add idea-detail.html
git commit -m "feat: sub-score bars in idea detail — demand/market/competition/trend/gtm"
```

---

## Task 4 — Регенерация одной идеи для проверки end-to-end

**Files:**
- No new files

- [ ] **Step 1: Запустить одну идею через новый пайплайн**

```bash
cd /Users/denismaskov/nota
python3 -c "
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv('.env', override=True)
from pipeline.run_launch_ideas import generate_idea
from pipeline.supabase_client import supabase
import json

seed = {'title': 'Протеиновые снеки нового поколения', 'query': 'protein snacks functional food', 'group': 'Питание'}
idea = generate_idea(seed)
if idea:
    detail = json.loads(idea['detail_json'])
    print('Score:', idea['score'])
    print('Sub-scores:', detail.get('sub_scores'))
    print('Structs keys:', list(detail.get('structs', {}).keys()))
    # Сохраняем
    supabase.table('launch_ideas').insert(idea).execute()
    print('Сохранено в Supabase')
"
```

Expected:
```
Score: <int 0-100>
Sub-scores: {'demand': <int>, 'market': <int>, 'competition': <int>, 'trend': <int>, 'gtm': <int>}
Structs keys: ['artem', 'petya', 'vova', 'avoska', 'polya']
Сохранено в Supabase
```

- [ ] **Step 2: Проверить в браузере**

Открой главную `http://localhost:3000`, найди новую идею, нажми на неё.  
Должны отображаться 5 цветных баров субскоров с весами.

- [ ] **Step 3: Final commit**

```bash
cd /Users/denismaskov/nota
git add -A
git commit -m "feat: end-to-end structured agents + rubric score verified"
```

---

## Self-Review

**Spec coverage:**
- ✅ Структурированный JSON от каждого агента → `structurer.py` + `structure_agent_output()`
- ✅ Рубрика балла с 5 субоценками и весами → `compute_score()`
- ✅ Балл не гадает Claude, а считается по данным → `computed_score`, Claude корректирует ±8
- ✅ Субскоры видны пользователю → `renderSubScores()` + CSS bars
- ✅ Существующие идеи не ломаются → `detail.sub_scores || {}` → заглушка

**Placeholder scan:** чисто — все функции содержат полный код.

**Type consistency:**
- `structure_agent_output` → возвращает `dict`
- `compute_score(structs: dict)` → принимает `{"artem": dict, ...}` → возвращает `(int, dict)`
- `detail.sub_scores` → `{"demand": int, "market": int, ...}` — везде одинаково
- `structs['artem']['trend_strength']` используется в Task 2 Step 2 и Task 1 Step 2 — совпадает
