"""
Запускает Авоську: генерирует 10 FMCG-инсайтов и сохраняет в Supabase trend_signals.
Запускать вручную или через GitHub Actions раз в неделю.
"""

import os
import sys
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'), override=True)

from pipeline.agents.avoska import get_weekly_insights
from pipeline.supabase_client import supabase


def run():
    print("[Авоська] Запуск еженедельного пайплайна...")
    insights = get_weekly_insights()

    if not insights:
        print("[Авоська] Нет инсайтов для сохранения. Проверь экспорты Telegram.")
        return

    print(f"[Авоська] Получено {len(insights)} инсайтов. Сохраняю в Supabase...")

    today = date.today().isoformat()

    # Удаляем старые инсайты Авоськи за сегодня (если уже запускали)
    # Фильтруем по source=telegram AND keyword начинается с известных заголовков — просто удаляем все telegram за сегодня с agent=Авоська в raw_data
    # Supabase не поддерживает фильтрацию по JSON-полю напрямую, поэтому удаляем все telegram за сегодня
    try:
        supabase.table('trend_signals').delete().eq('source', 'telegram').eq('date', today).execute()
    except Exception:
        pass  # Если удалить не удалось — просто добавим новые

    rows = []
    for ins in insights:
        rows.append({
            'keyword': ins.get('title', '')[:200],
            'source': 'telegram',
            'date': today,
            'raw_data': {
                'title': ins.get('title', ''),
                'summary': ins.get('summary', ''),
                'category': ins.get('category', ''),
                'importance': ins.get('importance', ''),
                'source_channel': ins.get('source_channel', ''),
                'agent': 'Авоська',
            },
        })

    res = supabase.table('trend_signals').insert(rows).execute()
    print(f"[Авоська] ✅ Сохранено {len(res.data)} инсайтов в trend_signals")
    for i, r in enumerate(res.data, 1):
        print(f"  {i}. {r.get('keyword', '')[:60]}")


if __name__ == '__main__':
    run()
