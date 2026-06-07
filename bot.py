"""
NOTA Telegram Bot — точка входа.
Свободный чат: все сообщения → Чукча → ответ.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Явно загружаем .env из папки проекта
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatAction

load_dotenv()

from pipeline.agents.chukcha import ask_chukcha
from pipeline.agents import memory

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

WELCOME = """👋 Привет! Я **NOTA Intelligence Bot**.

Нахожу FMCG-тренды и продуктовые ниши для России. Со мной работает команда агентов:

🔴 **Артём** — тренд-разведчик (TikTok, LinkedIn, YouTube, X/Twitter)
🔵 **Вова** — рыночный аналитик (WB, Ozon, Amazon) _—скоро—_
🟡 **Петя** — SEO-аналитик (Яндекс, Google Trends)
🛒 **Авоська** — FMCG гений (инсайты из профессиональных каналов)
🟣 **Поля** — маркетолог (упаковка идей под РФ) _—скоро—_
🟢 **Денис** — я, операционный директор, собираю всё в один ответ

Просто напиши что ищешь, например:
• _"Что хайпует в протеиновых снеках в США?"_
• _"Есть ли тренд на коллагеновые напитки в России?"_
• _"Найди идеи для запуска в категории снеки"_

/clear — очистить историю диалога"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    memory.clear_history(chat_id)
    await update.message.reply_text("🗑 История диалога очищена.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()

    if not user_text:
        return

    # Показываем что бот печатает
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        response = ask_chukcha(chat_id, user_text)

        # Telegram ограничивает 4096 символов — режем если нужно
        if len(response) > 4000:
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Что-то пошло не так. Попробуй ещё раз или /clear для сброса."
        )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 NOTA Bot запущен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
