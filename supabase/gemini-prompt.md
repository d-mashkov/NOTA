# Промпт для Gemini API — генерация NOTы

## Endpoint
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={{GEMINI_API_KEY}}

## Headers
Content-Type: application/json

## Request body (используй в Make.com → HTTP module)

```json
{
  "contents": [
    {
      "parts": [
        {
          "text": "Ты — аналитик FMCG-рынка России. На основе данных о трендах создай структурированный отчёт по продуктовой нише (NOTA).\n\nОтвечай ТОЛЬКО валидным JSON без markdown-обёртки, без ```json, только чистый JSON.\n\nКатегория: {{CATEGORY_NAME}}\nДата анализа: {{DATE}}\n\n### Данные Exa.ai (глобальные тренды EN):\n{{EXA_EN_DATA}}\n\n### Данные Exa.ai (тренды РФ):\n{{EXA_RU_DATA}}\n\nНа основе этих данных создай NOTA в JSON-формате:\n\n{\n  \"title\": \"Краткое название продуктовой ниши (до 60 символов)\",\n  \"description\": \"2-3 предложения: что это, почему актуально для России\",\n  \"trend_stage\": \"emerging | growing | hype | saturation\",\n  \"competition_level\": \"low | medium | high\",\n  \"recommendation\": \"launch | watch | skip\",\n  \"report\": {\n    \"foreign_cases\": \"Примеры успешных продуктов в США/Европе/Китае. Конкретные бренды.\",\n    \"demand_russia\": \"Анализ спроса в России: поисковые тренды, упоминания, интерес аудитории\",\n    \"demand_global\": \"Глобальный тренд: страны-лидеры, динамика роста\",\n    \"russian_market\": \"Анализ конкурентов в РФ: кто продаёт, цены, насколько развита ниша\",\n    \"competitors\": [\n      {\"name\": \"Название бренда\", \"segment\": \"масс-маркет/премиум\", \"price_range\": \"150-300 руб\"}\n    ],\n    \"target_audience\": \"ЦА: возраст, образ жизни, боли, мотивация к покупке\",\n    \"product_hypothesis\": \"Конкретная продуктовая гипотеза: что именно производить, в каком формате\",\n    \"flavors_formats\": \"Рекомендуемые вкусы, объёмы упаковки, форматы\",\n    \"market_size\": \"Оценка объёма рынка в рублях/штуках в год\",\n    \"launch_difficulty\": \"low | medium | high. Объяснение.\",\n    \"potential_margin\": \"Розничная цена, себестоимость, маржа %\",\n    \"risks\": \"Основные риски: регуляторные, конкурентные, сезонные\",\n    \"gtm\": \"Каналы выхода: Ozon, WB, ВкусВилл, фитнес-клубы. Приоритеты.\",\n    \"ai_output\": \"Финальный вывод-резюме. 4-6 предложений. Конкретный, без воды.\",\n    \"ai_recommendation\": \"Подробное обоснование рекомендации launch/watch/skip\",\n    \"sources\": [\n      {\"title\": \"Название источника\", \"url\": \"\", \"type\": \"exa | news | marketplace\"}\n    ]\n  },\n  \"score_breakdown\": {\n    \"demand_russia_growth\": 0,\n    \"foreign_confirmation\": 0,\n    \"marketplace_sales\": 0,\n    \"low_competition\": 0,\n    \"launch_simplicity\": 0,\n    \"potential_margin\": 0,\n    \"media_buzz\": 0,\n    \"fmcg_fit\": 0,\n    \"total\": 0\n  }\n}\n\nСкоринг (total = сумма всех):\n- demand_russia_growth: 0-20\n- foreign_confirmation: 0-15\n- marketplace_sales: 0-15\n- low_competition: 0-15\n- launch_simplicity: 0-10\n- potential_margin: 0-10\n- media_buzz: 0-10\n- fmcg_fit: 0-5\n\nБудь конкретным. Называй реальные бренды, цены, объёмы."
        }
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.3,
    "maxOutputTokens": 4096
  }
}
```

## Как извлечь JSON из ответа Gemini (Make.com → JSON Parse)

Путь к тексту ответа:
`candidates[0].content.parts[0].text`

Это будет чистый JSON — парсим через встроенный JSON модуль Make.com.
