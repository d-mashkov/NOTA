import sys
import traceback
from datetime import date
from pipeline.supabase_client import get_active_categories, save_note, save_note_report
from pipeline.exa_client import search_trends, format_results_for_prompt
from pipeline.telegram_loader import load_all_telegram_posts, search_relevant_posts, format_telegram_for_prompt
from pipeline.prompt import build_prompt
from pipeline.gemini_client import generate_nota


def run_pipeline(dry_run: bool = False) -> None:
    print(f"🚀 NOTA Pipeline started | {date.today()} | dry_run={dry_run}")

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
            print("  🔍 Searching Exa EN...")
            exa_en = search_trends(f"{cat_name_en} market trends FMCG", lang="en")
            exa_en_text = format_results_for_prompt(exa_en)

            print("  🔍 Searching Exa RU...")
            exa_ru = search_trends(" ".join(keywords[:3]), lang="ru")
            exa_ru_text = format_results_for_prompt(exa_ru)

            relevant_tg = search_relevant_posts(telegram_posts, keywords=keywords)
            tg_text = format_telegram_for_prompt(relevant_tg)
            print(f"  📱 Telegram matches: {len(relevant_tg)}")

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

            if not dry_run:
                note_id = save_note(cat_id, nota)
                save_note_report(note_id, nota["report"])
                print(f"  💾 Saved: note_id={note_id}")
            else:
                print(f"  [dry_run] Skipping save.")

            success_count += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            traceback.print_exc()
            error_count += 1

    print(f"\n✅ Done. Success: {success_count} | Errors: {error_count}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_pipeline(dry_run=dry_run)
