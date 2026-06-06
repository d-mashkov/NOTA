import json
from unittest.mock import patch, MagicMock
from pipeline.gemini_client import generate_nota

SAMPLE_NOTA = {
    "title": "ПП батончики без сахара",
    "description": "Растущий сегмент...",
    "trend_stage": "growing",
    "competition_level": "medium",
    "recommendation": "launch",
    "report": {
        "foreign_cases": "Kind bars, RxBar",
        "demand_russia": "Рост 35% г/г",
        "demand_global": "США лидер",
        "russian_market": "BioFoodLab, Bite",
        "competitors": [{"name": "Bite", "segment": "масс-маркет", "price_range": "80-120 руб"}],
        "target_audience": "25-35 лет",
        "product_hypothesis": "Батончик с финиками",
        "flavors_formats": "Шоколад, арахис",
        "market_size": "15 млрд руб/год",
        "launch_difficulty": "medium",
        "potential_margin": "60%",
        "risks": "Конкуренция",
        "gtm": "WB, Ozon",
        "ai_output": "Перспективная ниша",
        "ai_recommendation": "Запускать в Q3",
        "sources": [{"title": "Exa", "url": "", "type": "exa"}]
    },
    "score_breakdown": {
        "demand_russia_growth": 18, "foreign_confirmation": 14,
        "marketplace_sales": 12, "low_competition": 8,
        "launch_simplicity": 7, "potential_margin": 9,
        "media_buzz": 8, "fmcg_fit": 5, "total": 81
    }
}

def test_generate_nota_returns_dict():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(SAMPLE_NOTA, ensure_ascii=False)}]}}]
    }
    with patch("pipeline.gemini_client.requests.post", return_value=mock_response):
        result = generate_nota("Test prompt")
    assert result["title"] == "ПП батончики без сахара"
    assert result["score_breakdown"]["total"] == 81

def test_generate_nota_strips_markdown():
    wrapped = "```json\n" + json.dumps(SAMPLE_NOTA) + "\n```"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": wrapped}]}}]
    }
    with patch("pipeline.gemini_client.requests.post", return_value=mock_response):
        result = generate_nota("Test prompt")
    assert result["recommendation"] == "launch"
