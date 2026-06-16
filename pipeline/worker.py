"""
Worker — запускается в фоне API для обработки пользовательского запроса.
Использование: python worker.py <idea_id> <niche_text>
"""

import os
import sys
import json
import re

# Путь к корню проекта
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'), override=True)

from pipeline.supabase_client import supabase
from pipeline.run_launch_ideas import generate_idea


def classify_group(niche: str) -> str:
    """Определяет группу по ключевым словам в запросе."""
    n = niche.lower()
    if any(w in n for w in ["еда", "питан", "снек", "напит", "сок", "шокол", "сыр", "молок", "кофе", "чай", "food", "drink", "protein"]):
        return "Питание"
    if any(w in n for w in ["крем", "шампун", "уход", "beauty", "косметик", "кожа", "волос", "зуб", "дезодор"]):
        return "Уход"
    if any(w in n for w in ["гаджет", "трекер", "наушник", "телефон", "смарт", "device", "gadget", "tech"]):
        return "Гаджеты"
    if any(w in n for w in ["сигар", "вейп", "никотин", "табак", "снюс", "пауч", "pod"]):
        return "Никотин"
    if any(w in n for w in ["дом", "уборк", "стирк", "кухня", "посуд", "cleaning", "home"]):
        return "Дом"
    if any(w in n for w in ["сон", "постель", "подушк", "матрас", "lyocell", "tencel", "sleep", "bedding"]):
        return "Сон"
    return "FMCG"


def build_query(niche: str) -> str:
    """Строит поисковый запрос для агентов из текста ниши."""
    # Убираем стоп-слова и делаем компактный запрос
    stop = {"для", "с", "без", "в", "на", "по", "из", "и", "или", "нового", "новые", "новый"}
    words = [w for w in niche.split() if w.lower() not in stop]
    base = " ".join(words)
    return f"{base} Russia market 2025 D2C brand"


def main():
    if len(sys.argv) < 3:
        print("Usage: worker.py <idea_id> <niche_text>")
        sys.exit(1)

    idea_id = sys.argv[1]
    niche = " ".join(sys.argv[2:])

    print(f"[Worker] Запускаю анализ ниши: '{niche}' (id={idea_id})")

    try:
        group = classify_group(niche)
        query = build_query(niche)

        seed = {
            "title": niche,
            "query": query,
            "group": group,
        }

        result = generate_idea(seed)

        # Обновляем запись в Supabase — меняем статус на active
        supabase.table("launch_ideas").update({
            "status": "active",
            "title": result["title"],
            "category": result["category"],
            "summary": result["summary"],
            "score": result["score"],
            "artem": result.get("artem", ""),
            "petya": result.get("petya", ""),
            "vova": result.get("vova", ""),
            "avoska": result.get("avoska", ""),
            "polya": result.get("polya", ""),
            "detail_json": result["detail_json"],
        }).eq("id", idea_id).execute()

        print(f"[Worker] ✅ Готово! score={result['score']}")

    except Exception as e:
        print(f"[Worker] ❌ Ошибка: {e}")
        # Помечаем как failed чтобы фронтенд мог показать ошибку
        try:
            supabase.table("launch_ideas").update({
                "status": "failed",
                "summary": f"Ошибка анализа: {str(e)[:200]}",
            }).eq("id", idea_id).execute()
        except Exception:
            pass


if __name__ == "__main__":
    main()
