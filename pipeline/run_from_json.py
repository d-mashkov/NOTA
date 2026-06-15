"""
run_from_json.py — генерирует идею запуска из JSON-файла бренд-сессии.

Использование:
  python pipeline/run_from_json.py /path/to/bedding_brand_session.json
  python pipeline/run_from_json.py /path/to/file.json --title "Кастомное название"
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'), override=True)

from pipeline.run_launch_ideas import generate_idea
from pipeline.supabase_client import supabase


def extract_seed_from_json(data: dict, custom_title: str = None) -> dict:
    """Извлекает seed для агентов из произвольного JSON бренд-сессии."""

    # --- Пробуем стандартные поля нашей сессии ---
    brief = data.get("session_meta", {}).get("brief", {})
    naming = data.get("naming_exploration", {})

    # Название: custom > final_choice > первый кандидат из shortlist > project
    name = (
        custom_title
        or naming.get("final_choice", "").split(" ")[0]  # берём первое слово
        or (naming.get("shortlist") or [None])[0]
        or data.get("session_meta", {}).get("project", "Неизвестный продукт")
    )

    # Категория из brief
    category = brief.get("category", "")
    market = brief.get("market", "Russia")
    channel = brief.get("channel_and_tier", "D2C")
    aesthetic = brief.get("aesthetic_revised") or brief.get("aesthetic_initial", "")

    # Ключевая концепция из обоих брендов если есть
    concepts = []
    for key in data:
        if key.startswith("concept_"):
            concept = data[key]
            positioning = concept.get("positioning", {})
            if positioning.get("essence_statement_ru"):
                concepts.append(positioning["essence_statement_ru"])
            if positioning.get("mission"):
                concepts.append(positioning["mission"])

    # Строим query из всех найденных данных
    query_parts = [category, market, channel, aesthetic] + concepts[:1]
    query = " ".join(p for p in query_parts if p)[:200]

    # Группа по категории
    cat_lower = category.lower()
    if any(w in cat_lower for w in ["bed", "sleep", "lyocell", "постел", "сон"]):
        group = "Сон"
    elif any(w in cat_lower for w in ["food", "питание", "напит"]):
        group = "Питание"
    elif any(w in cat_lower for w in ["beauty", "skin", "красот", "уход"]):
        group = "Уход"
    elif any(w in cat_lower for w in ["home", "дом", "быт"]):
        group = "Дом"
    else:
        group = "Другое"

    # Формируем читаемый title
    if custom_title:
        title = custom_title
    else:
        # Берём название проекта из session_meta
        project = data.get("session_meta", {}).get("project", "")
        if project:
            # "Luxury/Mass-Premium Eucalyptus Bedding Brand — Russia/CIS"
            # → берём ключевую часть
            title = project.split("—")[0].strip()
        else:
            title = name

    return {
        "title": title,
        "query": query,
        "group": group,
        "_source_json": True,
        "_brand_name": name,
    }


def run(json_path: str, custom_title: str = None):
    # Читаем JSON
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    seed = extract_seed_from_json(data, custom_title)
    print(f"\n{'='*60}")
    print(f"[JSON→Идея] Файл: {json_path}")
    print(f"[JSON→Идея] Название: {seed['title']}")
    print(f"[JSON→Идея] Query: {seed['query'][:80]}...")
    print(f"[JSON→Идея] Группа: {seed['group']}")
    print(f"{'='*60}\n")

    # Если в JSON есть готовый бренд-контекст — передаём его агентам через query
    # Обогащаем query деталями бренда
    brand_context_parts = []
    for key in data:
        if key.startswith("concept_"):
            concept = data[key]
            pillars = concept.get("brand_pillars", [])
            for p in pillars[:2]:
                desc = p.get("desc_ru", "")
                if desc:
                    brand_context_parts.append(desc[:150])
            pricing = concept.get("positioning", {}).get("price_positioning", {})
            if pricing.get("label"):
                brand_context_parts.append(f"Ценовой сегмент: {pricing['label']}")

    if brand_context_parts:
        seed["query"] = seed["query"] + " | " + " | ".join(brand_context_parts[:2])
        seed["query"] = seed["query"][:300]

    # Генерируем идею через агентов
    idea = generate_idea(seed)

    if idea:
        # Сохраняем в Supabase
        supabase.table("launch_ideas").insert(idea).execute()
        print(f"\n[JSON→Идея] ✅ Сохранена: {idea['title']} (score: {idea['score']})")
    else:
        print("[JSON→Идея] ❌ Не удалось сгенерировать идею")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Генерация идеи из JSON-файла бренд-сессии")
    parser.add_argument("json_path", help="Путь к JSON-файлу")
    parser.add_argument("--title", help="Кастомное название идеи", default=None)
    args = parser.parse_args()

    run(args.json_path, args.title)
