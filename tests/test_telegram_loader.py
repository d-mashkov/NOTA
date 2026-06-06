import json
import tempfile
import os
from pipeline.telegram_loader import load_telegram_posts, search_relevant_posts, format_telegram_for_prompt

SAMPLE_EXPORT = {
    "name": "FMCG Report",
    "messages": [
        {"id": 1, "type": "message", "date": "2025-06-01T10:00:00", "text": "Протеиновые батончики — тренд 2025.", "views": 1500},
        {"id": 2, "type": "message", "date": "2025-05-15T12:00:00", "text": "Функциональные напитки захватывают рынок.", "views": 890},
        {"id": 3, "type": "service", "date": "2025-05-01T00:00:00", "text": ""},
    ]
}

def test_load_telegram_posts():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(SAMPLE_EXPORT, f, ensure_ascii=False)
        tmp_path = f.name
    try:
        posts = load_telegram_posts(tmp_path)
        assert len(posts) == 2
        assert posts[0]["channel"] == "FMCG Report"
        assert "батончики" in posts[0]["text"]
    finally:
        os.unlink(tmp_path)

def test_search_relevant_posts():
    posts = [
        {"channel": "FMCG", "date": "2025-06-01", "text": "Протеиновые батончики растут на 40%", "views": 1500},
        {"channel": "FMCG", "date": "2025-05-01", "text": "Функциональные напитки захватывают рынок", "views": 890},
        {"channel": "FMCG", "date": "2025-04-01", "text": "Зефир классический — стагнация", "views": 200},
    ]
    results = search_relevant_posts(posts, keywords=["батончик", "протеин"])
    assert len(results) == 1
    assert "батончики" in results[0]["text"]

def test_format_telegram_for_prompt():
    posts = [{"channel": "FMCG", "date": "2025-06-01", "text": "Тест", "views": 100}]
    output = format_telegram_for_prompt(posts)
    assert "FMCG" in output
    assert "Тест" in output

def test_format_empty_returns_empty_string():
    assert format_telegram_for_prompt([]) == ""
