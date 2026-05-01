import os
import logging
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
BOT_NAME = os.environ.get("BOT_NAME", "AI Ассистент")
BOT_PERSONALITY = os.environ.get("BOT_PERSONALITY", """Ты дружелюбный и умный AI-ассистент. 
Отвечай на русском языке если пользователь пишет по-русски, на английском — если по-английски.
Будь полезным, интересным и немного с юмором. Отвечай кратко и по делу.""")

groq_client = Groq(api_key=GROQ_API_KEY)

# Хранилище истории диалогов
conversation_history: dict[int, list] = {}
MAX_HISTORY = 20


def get_ai_response(user_id: int, user_message: str) -> str:
    """Получить ответ от Groq с учётом истории диалога."""
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    if len(conversation_history[user_id]) > MAX_HISTORY:
        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]

    messages = [{"role": "system", "content": BOT_PERSONALITY}] + conversation_history[user_id]

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1000,
    )

    assistant_message = response.choices[0].message.content

    conversation_history[user_id].append({
        "role": "assistant",
        "content": assistant_message
    })

    return assistant_message


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    conversation_history[user.id] = []
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}! Я {BOT_NAME}.\n\n"
        "Просто напиши мне что-нибудь, и я отвечу!\n\n"
        "Команды:\n"
        "/start — начать заново\n"
        "/reset — очистить историю диалога\n"
        "/help — помощь"
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conversation_history[update.effective_user.id] = []
    await update.message.reply_text("🔄 История диалога очищена! Начнём с чистого листа.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"🤖 *{BOT_NAME}*\n\n"
        "Просто напиши мне любое сообщение — я отвечу!\n"
        "Я помню контекст нашего разговора.\n\n"
        "*/start* — начать заново\n"
        "*/reset* — очистить историю\n"
        "*/help* — это сообщение",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        response = get_ai_response(user_id, user_message)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error getting AI response: {e}")
        await update.message.reply_text("😅 Что-то пошло не так. Попробуй ещё раз!")


def main() -> None:
    logger.info(f"Starting {BOT_NAME}...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
