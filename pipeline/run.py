import sys
import traceback
from datetime import date
from pipeline.supabase_client import get_active_categories, save_note, save_note_report
from pipeline.exa_client import search_trends, format_results_for_prompt
from pipeline.telegram_loader import load_all_telegram_posts, search_relevant_posts, format_telegram_for_prompt
from pipeline.youtube_client import search_youtube, format_youtube_for_prompt
from pipeline.social_client import search_tiktok, search_linkedin, format_social_for_prompt
from pipeline.prompt import build_prompt
from pipeline.gemini_client import generate_nota
from pipeline.config import YOUTUBE_API_KEY


def run_pipeline(dry_run: bool = False) -> None:
    print(f"🚀 NOTA Pipeline started | {date.today()} | dry_run={dry_run}")

    # Загружаем Telegram посты один раз для всех категорий
    telegram_posts = load_all_telegram_posts()
    print(f"📱 Telegram (manual exports): {len(telegram_posts)} posts")

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
            # 1. Exa EN — глобальные тренды
            print("  🔍 Exa EN...")
            exa_en = search_trends(f"{cat_name_en} FMCG market trends consumers", lang="en")
            exa_en_text = format_results_for_prompt(exa_en)

            # 2. Exa RU — российский рынок
            print("  🔍 Exa RU...")
            exa_ru = search_trends(" ".join(keywords[:3]), lang="ru")
            exa_ru_text = format_results_for_prompt(exa_ru)

            # 3. Telegram (ручной экспорт JSON)
            relevant_tg = search_relevant_posts(telegram_posts, keywords=keywords)
            tg_text = format_telegram_for_prompt(relevant_tg)
            print(f"  📱 Telegram matches: {len(relevant_tg)}")

            # 4. YouTube
            youtube_text = ""
            if YOUTUBE_API_KEY:
                print("  🎥 YouTube...")
                yt_ru = search_youtube(f"{cat_name} тренд обзор", max_results=6)
                yt_en = search_youtube(f"{cat_name_en} trend review", max_results=6)
                youtube_text = format_youtube_for_prompt(yt_ru + yt_en)
                print(f"  🎥 YouTube: {len(yt_ru + yt_en)} videos")
            else:
                print("  🎥 YouTube: пропуск (нет API ключа)")

            # 5. TikTok (через Exa)
            print("  🎵 TikTok...")
            tiktok = search_tiktok(f"{cat_name_en} {cat_name}")
            print(f"  🎵 TikTok: {len(tiktok)} results")

            # 6. LinkedIn (через Exa)
            print("  💼 LinkedIn...")
            linkedin = search_linkedin(f"{cat_name_en} market Russia")
            print(f"  💼 LinkedIn: {len(linkedin)} results")

            social_text = format_social_for_prompt(tiktok, linkedin)

            # 7. Строим промпт со всеми данными
            prompt = build_prompt(
                category_name=cat_name,
                category_name_en=cat_name_en,
                exa_en_data=exa_en_text,
                exa_ru_data=exa_ru_text,
                telegram_data=tg_text,
                youtube_data=youtube_text,
                tiktok_data=social_text,
            )

            # 8. Gemini генерирует NOTA
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
