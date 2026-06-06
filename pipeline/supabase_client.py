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
