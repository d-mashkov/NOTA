# НОТА — FMCG Trend Intelligence

## Быстрый старт

### 1. Подключить Supabase
Открой `js/supabase-client.js` и замени:
```js
const SUPABASE_URL  = 'https://YOUR_PROJECT.supabase.co';
const SUPABASE_ANON = 'YOUR_ANON_KEY';
```
Данные — в Supabase Dashboard → Settings → API.

### 2. Создать таблицы в Supabase
Открой Supabase → SQL Editor → вставь содержимое `supabase/schema.sql` → Run.

### 3. Добавить себя как admin
В Supabase → Table Editor → users → Insert row:
```
email: твой@email.com
name: Denis
role: admin
is_active: true
```

### 4. Включить Email Auth в Supabase
Supabase → Authentication → Providers → Email → включить "Magic Link".

### 5. Запустить локально
```bash
npx serve .
# или просто открой index.html через Live Server в VS Code
```

## Структура проекта
```
nota/
├── index.html        — Dashboard
├── notes.html        — Лента НОТ
├── note.html         — Карточка НОТЫ (20 блоков)
├── login.html        — Авторизация
├── admin.html        — Панель администратора
├── css/
│   └── main.css      — Вся стилевая система
├── js/
│   └── supabase-client.js  — Supabase + хелперы
└── supabase/
    ├── schema.sql          — Структура БД
    └── yandexgpt-prompt.md — Промпт для AI
```

## Следующий шаг — Make.com
Настройка сценария парсинга в `make-scenario.md` (будет добавлен).
