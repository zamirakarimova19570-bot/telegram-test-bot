import os
import re
import logging
from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# .env faylni yuklash (agar mavjud bo'lsa)
load_dotenv()

# Bot tokenini olish
BOT_TOKEN = os.getenv("8577664982:AAFIz8yMn-4SHLCCtFXvDOmHYG8PkIz5SEg")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisi topilmadi. .env faylini tekshiring.")

# Spam kalit so'zlar (pastki registerda)
SPAM_KEYWORDS = [
    "t.me/", "telegram.me/", "join chat", "obuna bo'ling", "pul ishlash",
    "kredit", "kriptovalyuta", "investitsiya", "daromad", "18+", "onlyfans",
    "reklama", "bot qo'shing", "kanalga a'zo bo'ling", "click", "bonus", "tez pul"
]

# URL/Linklarni aniqlash uchun regex
URL_PATTERN = re.compile(r'https?://[^\s]+|www\.[^\s]+|t\.me/[^\s]+', re.IGNORECASE)

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.chat or message.chat.type == "private":
        return  # Shaxsiy chatlarda ishlamaydi

    user = message.from_user
    text = (message.text or message.caption or "").lower()

    # Link (URL) tekshiruvi
    if URL_PATTERN.search(message.text or message.caption or ""):
        await delete_and_warn(message, user, "🔗 Link yuborish taqiqlangan!")
        return

    # Spam kalit so'zlarini tekshirish
    for word in SPAM_KEYWORDS:
        if word in text:
            await delete_and_warn(message, user, f"❌ '{word.strip()}' so'zi taqiqlangan!")
            return

async def delete_and_warn(message, user, reason: str):
    try:
        # Xabarni o'chirish
        await message.delete()
        # Ogohlantirish xabarini yuborish
        warn_msg = await message.reply_text(
            f"⚠️ {user.mention_html()} — {reason}\n"
            "Guruh qoidalariga rioya qiling!",
            parse_mode="HTML"
        )
        # 10 soniyadan so'ng ogohlantiruvchi xabarni o'chirish
        context.job_queue.run_once(lambda _: warn_msg.delete(), 10)
    except Exception as e:
        logger.warning(f"Xabar o'chirishda xatolik: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.Caption, check_message))
    logger.info("🧹 CleanGroupBot ishga tushdi! Guruhga admin sifatida qo'shing.")
    app.run_polling()

if __name__ == "__main__":
    main()
