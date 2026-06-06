from pipeline.prompt import build_prompt

def test_build_prompt_contains_all_sections():
    prompt = build_prompt(
        category_name="ПП батончики",
        category_name_en="Protein bars",
        exa_en_data="1. Protein bars growing fast",
        exa_ru_data="1. Батончики без сахара в тренде",
        telegram_data="[FMCG Report | 2025-06-01 | 👁 1500]\nПротеиновые батончики растут.",
    )
    assert "ПП батончики" in prompt
    assert "Protein bars" in prompt
    assert "Protein bars growing fast" in prompt
    assert "Батончики без сахара" in prompt
    assert "FMCG Report" in prompt
    assert "demand_russia_growth" in prompt
    assert "total" in prompt

def test_build_prompt_without_telegram():
    prompt = build_prompt(
        category_name="Зефир",
        category_name_en="Marshmallow",
        exa_en_data="Some EN data",
        exa_ru_data="Some RU data",
        telegram_data="",
    )
    assert "Зефир" in prompt
    assert "Telegram" not in prompt
    assert len(prompt) > 500
