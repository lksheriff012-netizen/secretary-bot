import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from datetime import datetime

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"
GROQ_API_KEY = "ВАШ_КЛЮЧ_GROQ"
# ================================

logging.basicConfig(level=logging.INFO)
client = Groq(api_key=GROQ_API_KEY)

# Хранилище задач в памяти
tasks = []

SYSTEM_PROMPT = """Ты — умный личный секретарь руководителя отдела продаж. 
Твои задачи:
1. Когда тебе пересылают сообщения из рабочих чатов — вычленяй задачи, дедлайны, важные решения
2. Расставляй приоритеты: 🔴 срочно (сегодня-завтра), 🟡 важно (эта неделя), 🟢 можно отложить
3. Отвечай кратко и по делу, используй эмодзи для наглядности
4. Если видишь дедлайн — всегда выдели его отдельно с датой
5. Говори на русском языке

Формат ответа при анализе сообщения:
📋 ЗАДАЧИ:
• [приоритет] задача — дедлайн если есть

⚡ ТРЕБУЕТ ОТВЕТА СЕГОДНЯ: (если есть)

💡 МОЖНО ОТЛОЖИТЬ: (если есть)"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я твой секретарь.\n\n"
        "Что умею:\n"
        "• Перешли мне любое рабочее сообщение — вычленю задачи и дедлайны\n"
        "• /summary — сводка задач за день\n"
        "• /tasks — все активные задачи\n"
        "• /clear — очистить список задач\n\n"
        "Просто перешли сообщение из рабочего чата! 👇"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    now = datetime.now().strftime("%H:%M %d.%m")

    # Сохраняем в историю задач
    tasks.append({"time": now, "text": user_text[:100]})

    # Отправляем в Groq
    await update.message.reply_text("⏳ Анализирую...")

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Проанализируй это рабочее сообщение:\n\n{user_text}"}
            ],
            max_tokens=800
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tasks:
        await update.message.reply_text("📭 Сегодня задач ещё не было.")
        return

    tasks_text = "\n".join([f"[{t['time']}] {t['text']}" for t in tasks[-20:]])

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Сделай сводку дня по этим задачам. Что сделано, что срочно, что можно перенести:\n\n{tasks_text}"}
            ],
            max_tokens=800
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(f"📊 СВОДКА ДНЯ\n\n{reply}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tasks:
        await update.message.reply_text("📭 Список задач пуст.")
        return

    text = "📋 Последние задачи:\n\n"
    for t in tasks[-10:]:
        text += f"[{t['time']}] {t['text']}\n"
    await update.message.reply_text(text)


async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks.clear()
    await update.message.reply_text("🗑 Список задач очищен.")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("tasks", show_tasks))
    app.add_handler(CommandHandler("clear", clear_tasks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен!")
    app.run_polling()
