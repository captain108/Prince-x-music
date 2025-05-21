import os
import json
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

# === Config ===
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("ADMIN_ID", "123456789"))  # Set this in Render
PORT = int(os.getenv("PORT", 8443))  # Render sets this automatically
CHAT_DB_FILE = "chat_ids.json"

# === Flask for uptime ping ===
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Telegram Bot is running!"

# === Chat ID Storage ===
def load_chat_ids():
    if os.path.exists(CHAT_DB_FILE):
        with open(CHAT_DB_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_chat_ids(ids):
    with open(CHAT_DB_FILE, "w") as f:
        json.dump(list(ids), f)

chat_ids = load_chat_ids()

# === Telegram Handlers ===
async def save_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid not in chat_ids:
        chat_ids.add(cid)
        save_chat_ids(chat_ids)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_chat(update, context)
    await update.message.reply_text("You're now subscribed to broadcasts!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    count, failed = 0, 0

    if update.message.reply_to_message:
        original = update.message.reply_to_message
        for cid in chat_ids:
            try:
                await context.bot.copy_message(chat_id=cid,
                                               from_chat_id=original.chat.id,
                                               message_id=original.message_id)
                count += 1
            except:
                failed += 1
    elif context.args:
        msg = ' '.join(context.args)
        for cid in chat_ids:
            try:
                await context.bot.send_message(chat_id=cid, text=msg)
                count += 1
            except:
                failed += 1
    else:
        await update.message.reply_text("❗ Use /broadcast <text> or reply to a message to send.")
        return

    await update.message.reply_text(f"✅ Broadcast complete.\nSent: {count} chats\nFailed: {failed}")

# === App setup ===
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(MessageHandler(filters.ALL, save_chat))

# === Run both Flask and Bot ===
if __name__ == "__main__":
    async def run_bot():
        await application.initialize()
        await application.start()
        print("Bot started.")
        await application.updater.start_polling()
        await application.updater.wait()

    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    flask_app.run(host="0.0.0.0", port=PORT)
