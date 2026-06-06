import json
import requests
from pipeline.config import GEMINI_API_KEY, GEMINI_API_URL


def generate_nota(prompt: str) -> dict:
    """
    Отправляет промпт в Gemini API и возвращает распарсенный JSON с NOTой.
    """
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
    }

    response = requests.post(
        GEMINI_API_URL,
        json=payload,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()

    raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
    if raw_text.endswith("```"):
        raw_text = raw_text.rsplit("```", 1)[0]

    return json.loads(raw_text)
