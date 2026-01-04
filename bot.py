from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re
import os

# BOT_TOKEN ni bu yerda yoki .env orqali qo'ying
BOT_TOKEN = "8577664982:AAFIz8yMn-4SHLCCtFXvDOmHYG8PkIz5SEg"

# Bloklanadigan kalit so'zlar va patternlar
SPAM_KEYWORDS = [
    "t.me/", "telegram.me/", "join chat", "obuna bo'ling", "pul ishlash",
    "kredit", "kriptovalyuta", "investitsiya", "daromad", "18+", "onlyfans",
    "reklama", "bot qo'shing", "kanalga a'zo bo'ling"
]

# Linklarni topish uchun regex
URL_PATTERN = re.compile(r'https?://[^\s]+|www\.[^\s]+|t\.me/[^\s]+')

async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.chat or message.chat.type == "private":
        return  # Shaxsiy chatlarda ishlamaydi

    user = message.from_user
    text = (message.text or message.caption or "").lower()

    # Agar xabar link (URL) qamrab olsa
    if URL_PATTERN.search(message.text or message.caption or ""):
        await delete_and_warn(message, user, "🔗 Link yuborish taqiqlangan!")
        return

    # Agar spam kalit so'zlari bo'lsa
    for word in SPAM_KEYWORDS:
        if word in text:
            await delete_and_warn(message, user, f"❌ '{word}' so'zi taqiqlangan!")
            return

async def delete_and_warn(message, user, reason: str):
    try:
        await message.delete()
        warn_msg = await message.reply_text(
            f"⚠️ {user.mention_html()} — {reason}\n"
            "Guruh qoidalariga rioya qiling!",
            parse_mode="HTML"
        )
        # 10 soniyadan so'ng ogohlantiruvchi xabarni o'chirish
        context.job_queue.run_once(lambda _: warn_msg.delete(), 10)
    except Exception as e:
        print(f"Xatolik: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.Caption, check_message))
    print("🧹 CleanGroupBot ishga tushdi! Guruhga admin sifatida qo'shing.")
    app.run_polling()

if __name__ == "__main__":
    main()
