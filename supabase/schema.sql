-- ============================================
-- NOTA — Supabase Schema v1.0
-- ============================================

-- 1. ПОЛЬЗОВАТЕЛИ
create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  name text,
  role text not null default 'user' check (role in ('admin', 'analyst', 'user')),
  is_active boolean default true,
  created_at timestamptz default now()
);

-- 2. КАТЕГОРИИ (seed-категории для анализа)
create table if not exists categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  name_en text,
  seed_queries text[], -- массив ключевых слов для парсинга
  is_active boolean default true,
  last_analyzed_at timestamptz,
  created_at timestamptz default now()
);

-- 3. СИГНАЛЫ ТРЕНДОВ (сырые данные от парсеров)
create table if not exists trend_signals (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('wordstat', 'google_trends', 'google_news', 'ozon', 'wb', 'serpapi')),
  keyword text not null,
  keyword_en text,
  country text default 'RU',
  category_id uuid references categories(id),
  value numeric, -- частотность / индекс
  growth_rate numeric, -- % роста
  date date default current_date,
  confidence integer default 50 check (confidence between 0 and 100),
  raw_data jsonb, -- полный ответ API
  created_at timestamptz default now()
);

-- 4. НОТЫ (основные карточки)
create table if not exists notes (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  category_id uuid references categories(id),
  description text,
  score integer default 0 check (score between 0 and 100),
  status text default 'draft' check (status in ('draft', 'published', 'archived')),
  trend_stage text check (trend_stage in ('emerging', 'growing', 'hype', 'saturation')),
  competition_level text check (competition_level in ('low', 'medium', 'high')),
  recommendation text check (recommendation in ('launch', 'watch', 'skip')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 5. ДЕТАЛЬНЫЙ ОТЧЁТ НОТЫ (20 блоков)
create table if not exists note_reports (
  id uuid primary key default gen_random_uuid(),
  note_id uuid references notes(id) on delete cascade,

  -- Спрос
  demand_russia jsonb,        -- динамика РФ: [{date, value, growth}]
  demand_global jsonb,        -- динамика глобал: [{country, value, trend}]

  -- Аналитика
  foreign_cases text,         -- примеры успешных продуктов за рубежом
  russian_market text,        -- анализ конкурентов в РФ
  competitors jsonb,          -- [{name, link, price, share}]
  marketplace_data jsonb,     -- данные Ozon/WB

  -- Продуктовая гипотеза
  product_hypothesis text,    -- рекомендуемый формат продукта
  target_audience text,       -- ЦА
  flavors_formats text,       -- вкусы, форматы, объёмы
  gtm text,                   -- каналы выхода на рынок

  -- Оценки
  market_size text,           -- оценка рынка
  launch_difficulty text,     -- сложность запуска
  potential_margin text,      -- потенциальная маржа
  risks text,                 -- риски

  -- AI-вывод
  ai_output text,             -- полный текст от YandexGPT/Claude
  ai_recommendation text,     -- launch / watch / skip с обоснованием

  -- Мета
  sources jsonb,              -- [{title, url, type}]
  updated_at timestamptz default now()
);

-- 6. СОХРАНЁННЫЕ НОТЫ
create table if not exists saved_notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  note_id uuid references notes(id) on delete cascade,
  comment text,
  saved_at timestamptz default now(),
  unique(user_id, note_id)
);

-- 7. КОММЕНТАРИИ К НОТАМ
create table if not exists note_comments (
  id uuid primary key default gen_random_uuid(),
  note_id uuid references notes(id) on delete cascade,
  user_id uuid references users(id) on delete cascade,
  text text not null,
  created_at timestamptz default now()
);

-- ============================================
-- SEED DATA — первые 3 категории для MVP
-- ============================================

insert into categories (name, name_en, seed_queries, is_active) values
(
  'ПП батончики',
  'Protein bars',
  array['пп батончик', 'протеиновый батончик', 'батончик без сахара', 'спортивный батончик', 'батончик мюсли'],
  true
),
(
  'Туалетная бумага',
  'Toilet paper',
  array['туалетная бумага', 'бамбуковая туалетная бумага', 'влажная туалетная бумага', 'безотходная туалетная бумага'],
  true
),
(
  'Функциональные напитки',
  'Functional drinks',
  array['функциональный напиток', 'напиток с коллагеном', 'напиток с электролитами', 'адаптогены напиток', 'ноотропный напиток'],
  true
);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

alter table notes enable row level security;
alter table note_reports enable row level security;
alter table saved_notes enable row level security;
alter table note_comments enable row level security;

-- Читать опубликованные ноты могут все авторизованные
create policy "Read published notes" on notes
  for select using (status = 'published');

-- Комментарии видят все, пишет только владелец
create policy "Read comments" on note_comments
  for select using (true);

create policy "Write own comments" on note_comments
  for insert with check (auth.uid()::text = user_id::text);

-- Сохранённые ноты — только свои
create policy "Own saved notes" on saved_notes
  for all using (auth.uid()::text = user_id::text);
