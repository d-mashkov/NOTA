-- Таблица пользователей Telegram-бота
CREATE TABLE IF NOT EXISTS telegram_users (
    id          BIGSERIAL PRIMARY KEY,
    chat_id     BIGINT UNIQUE NOT NULL,
    username    TEXT DEFAULT '',
    first_name  TEXT DEFAULT '',
    last_name   TEXT DEFAULT '',
    first_seen  TIMESTAMPTZ DEFAULT NOW(),
    last_seen   TIMESTAMPTZ DEFAULT NOW(),
    message_count INTEGER DEFAULT 1
);

-- Функция для инкремента счётчика сообщений
CREATE OR REPLACE FUNCTION increment_message_count(user_chat_id BIGINT)
RETURNS VOID AS $$
BEGIN
    UPDATE telegram_users
    SET message_count = message_count + 1,
        last_seen = NOW()
    WHERE chat_id = user_chat_id;
END;
$$ LANGUAGE plpgsql;
