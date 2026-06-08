-- Добавляем detail_json в launch_ideas для хранения детальной аналитики
ALTER TABLE launch_ideas ADD COLUMN IF NOT EXISTS detail_json TEXT DEFAULT NULL;
