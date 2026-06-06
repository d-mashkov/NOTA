from unittest.mock import patch, MagicMock
from pipeline.exa_client import search_trends, format_results_for_prompt

def test_search_trends_returns_results():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"title": "Protein bar market growing", "url": "https://example.com", "text": "Long article..."},
            {"title": "Keto bars trend 2024", "url": "https://example2.com", "text": "Another article..."},
        ]
    }
    with patch("pipeline.exa_client.requests.post", return_value=mock_response):
        result = search_trends("protein bars", lang="en")
    assert len(result) == 2
    assert result[0]["title"] == "Protein bar market growing"

def test_search_trends_empty_results():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    with patch("pipeline.exa_client.requests.post", return_value=mock_response):
        result = search_trends("unknown niche xyz", lang="ru")
    assert result == []

def test_format_results_for_prompt():
    results = [
        {"title": "Title 1", "url": "https://a.com", "text": 'Text with "quotes"'},
        {"title": "Title 2", "url": "https://b.com", "text": "Clean text"},
    ]
    output = format_results_for_prompt(results)
    assert "Title 1" in output
    assert "Title 2" in output
    assert '"' not in output  # кавычки заменены на апострофы

def test_format_empty_results():
    assert format_results_for_prompt([]) == "Данные не найдены."
