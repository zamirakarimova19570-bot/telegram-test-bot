from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import asyncio
import re
from datetime import datetime
import time
import json
import os
import logging

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Konstantsalar
TEST_KOD_UZUNLIGI = 5
MAX_SAVOL_SONI = 50

# Bot tokeni
TOKEN = os.getenv('BOT_TOKEN', '8204543466:AAGBxKvrTRx3N8zOtoonRxafZPTSEPZLhDI')

print("=" * 60)
print("🚀 GITHUB ACTIONS - TELEGRAM TEST BOT")
print("Mironshoh testlar boti")
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("📍 Server: GitHub Actions")
print("⏰ Uptime: 24/7")
print(" 7 - A sinf oquvchisi")
print("=" * 60)

# Memory Database (SQLite o'rniga)
tests_db = {}  # test_kod -> test_malumotlari
user_sessions = {}  # user_id -> session
user_data_store = {}  # user_id -> context_data

class MemoryDatabase:
    @staticmethod
    def save_test(test_kod: str, ustoz_id: int, ustoz_username: str, savollar: list):
        tests_db[test_kod] = {
            'ustoz_id': ustoz_id,
            'ustoz_username': ustoz_username,
            'savollar': savollar,
            'yaratilgan_vaqt': datetime.now().isoformat(),
            'status': 'active'
        }
        return True
    
    @staticmethod
    def get_test(test_kod: str):
        return tests_db.get(test_kod)
    
    @staticmethod
    def save_session(user_id: int, test_kod: str, current_savol: int):
        user_sessions[user_id] = {
            'test_kod': test_kod,
            'current_savol': current_savol,
            'last_activity': time.time(),
            'status': 'active'
        }
    
    @staticmethod
    def get_session(user_id: int):
        return user_sessions.get(user_id)
    
    @staticmethod
    def update_session_activity(user_id: int):
        if user_id in user_sessions:
            user_sessions[user_id]['last_activity'] = time.time()
    
    @staticmethod
    def delete_session(user_id: int):
        if user_id in user_sessions:
            del user_sessions[user_id]
    
    @staticmethod
    def save_result(user_id: int, test_kod: str, togri_javoblar: int, total_savollar: int):
        # Faqat log qilamiz
        logger.info(f"Natija: user_id={user_id}, test_kod={test_kod}, togri={togri_javoblar}/{total_savollar}")
    
    @staticmethod
    def get_user_tests(ustoz_id: int):
        return [test for test in tests_db.values() if test['ustoz_id'] == ustoz_id]

db = MemoryDatabase()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    keyboard = [
        [InlineKeyboardButton("👨‍🎓 O'quvchi", callback_data='oquvchi')],
        [InlineKeyboardButton("👨‍🏫 Ustoz", callback_data='ustoz')],
        [InlineKeyboardButton("📋 Yaratilgan testlar", callback_data='my_tests')]
    ]
    
    await update.message.reply_text(
        "Test botga xush kelibsiz! Rolni tanlang:\n\n"
        "📊 *Server holati:*\n"
        f"• Platforma: GitHub Actions\n"
        f"• Uptime: 24/7 (avtomatik restart)\n"
        f"• Narx: Umrbod bepul\n\n"
        "⚠️ *Eslatma:* Test GitHub memory da saqlanadi!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == 'oquvchi':
        await query.edit_message_text(
            "Test kodini kiriting (5 ta harf/raqam):\n\n"
            "Namuna: ABC12 yoki 123DE\n\n"
            "Mavjud testlar:\n" + 
            "\n".join([f"• {k}" for k in tests_db.keys()]) if tests_db else "• Hozircha test yo'q"
        )
        user_data_store[user_id] = {'mode': 'student_waiting_code'}
    
    elif data == 'ustoz':
        await query.edit_message_text(
            "Ustoz rejimi:\n\n"
            "1. Yangi test yaratish uchun /new_test\n"
            "2. Mening testlarim uchun /my_tests\n"
            "3. Test natijalari uchun /results"
        )
    
    elif data == 'my_tests':
        user_tests = db.get_user_tests(user_id)
        if user_tests:
            tests_info = "📋 *Siz yaratgan testlar:*\n\n"
            for test in user_tests:
                tests_info += f"🔹 *Test kodi:* `{list(tests_db.keys())[list(tests_db.values()).index(test)]}`\n"
                tests_info += f"   📅 {test['yaratilgan_vaqt'][:16]}\n"
                tests_info += f"   ❓ Savollar: {len(test['savollah'])} ta\n"
                tests_info += "   ────────────────\n"
            
            await query.edit_message_text(
                tests_info,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👨‍🏫 Yangi test", callback_data='ustoz')],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data='menu')]
                ])
            )
        else:
            await query.edit_message_text(
                "Siz hali test yaratmagansiz.\nYangi test yaratish uchun /new_test",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👨‍🏫 Yangi test", callback_data='ustoz')]
                ])
            )
    
    elif data == 'menu':
        keyboard = [
            [InlineKeyboardButton("👨‍🎓 O'quvchi", callback_data='oquvchi')],
            [InlineKeyboardButton("👨‍🏫 Ustoz", callback_data='ustoz')],
            [InlineKeyboardButton("📋 Yaratilgan testlar", callback_data='my_tests')]
        ]
        await query.edit_message_text(
            "Bosh menyu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data in ['next_question', 'finish_test', 'variant', 'yozma', 'retry_question']:
        await handle_teacher_actions(query, data, context)

async def handle_teacher_actions(query, data, context):
    user_id = query.from_user.id
    
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    
    if data == 'next_question':
        if 'current_test_kod' in user_data_store[user_id]:
            test_kod = user_data_store[user_id]['current_test_kod']
            current = user_data_store[user_id].get('savol_nomeri', 1)
            user_data_store[user_id]['savol_nomeri'] = current + 1
            
            if current + 1 <= MAX_SAVOL_SONI:
                await query.edit_message_text(
                    f"Savol #{current + 1}:\n1. Savol matnini kiriting:"
                )
                user_data_store[user_id]['step'] = 'savol_matni'
            else:
                await query.edit_message_text(
                    f"✅ Maksimum {MAX_SAVOL_SONI} ta savol!\nTest kodi: `{test_kod}`",
                    parse_mode='Markdown'
                )
    
    elif data == 'finish_test':
        if 'current_test_kod' in user_data_store[user_id]:
            test_kod = user_data_store[user_id]['current_test_kod']
            savollar = user_data_store[user_id].get('savollar', [])
            
            if savollar:
                db.save_test(
                    test_kod,
                    user_id,
                    user_data_store[user_id].get('ustoz_username', ''),
                    savollar
                )
            
            await query.edit_message_text(
                f"✅ Test yaratildi! Kodi: `{test_kod}`\n"
                f"Savollar soni: {len(savollar)}",
                parse_mode='Markdown'
            )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # O'quvchi test kodi kiritish
    if user_id in user_data_store and user_data_store[user_id].get('mode') == 'student_waiting_code':
        test_code = text.upper()
        test_data = db.get_test(test_code)
        
        if test_data:
            # Testni boshlash
            db.save_session(user_id, test_code, 1)
            user_data_store[user_id] = {
                'test_kod': test_code,
                'current_savol': 1,
                'togri_javoblar': 0,
                'mode': 'in_test'
            }
            
            await send_savol(update, context, user_id, test_code, 1)
        else:
            await update.message.reply_text(
                f"❌ '{test_code}' test kodi topilmadi.\n"
                f"Mavjud testlar: {', '.join(tests_db.keys()) if tests_db else 'yoq'}"
            )
        return
    
    # O'quvchi testda javob berish
    elif user_id in user_data_store and user_data_store[user_id].get('mode') == 'in_test':
        await handle_student_answer(update, context, user_id, text)
        return
    
    # Ustoz test yaratish
    if text.startswith('/new_test'):
        await update.message.reply_text(
            "Yangi test yaratish:\n\n"
            "1. Test kodi (5 ta harf/raqam):"
        )
        user_data_store[user_id] = {'step': 'test_kodi'}
    
    elif user_id in user_data_store and user_data_store[user_id].get('step') == 'test_kodi':
        if len(text) == 5 and re.match(r'^[A-Za-z0-9]+$', text):
            test_kod = text.upper()
            
            if db.get_test(test_kod):
                await update.message.reply_text("Bu test kodi band. Boshqa kiriting:")
            else:
                user_data_store[user_id] = {
                    'current_test_kod': test_kod,
                    'savol_nomeri': 1,
                    'savollar': [],
                    'step': 'ustoz_username'
                }
                await update.message.reply_text(
                    f"✅ Test kodi: {test_kod}\n"
                    f"Ustoz username kiriting (@ bilan):"
                )
        else:
            await update.message.reply_text(
                f"❌ Noto'g'ri format! 5 ta harf/raqam bo'lishi kerak."
            )
    
    elif user_id in user_data_store and user_data_store[user_id].get('step') == 'ustoz_username':
        if text.startswith('@'):
            user_data_store[user_id]['ustoz_username'] = text
            user_data_store[user_id]['step'] = 'savol_matni'
            await update.message.reply_text(
                f"✅ Username qabul qilindi: {text}\n\n"
                f"Savol #{user_data_store[user_id]['savol_nomeri']}:\n"
                f"1. Savol matnini kiriting:"
            )
        else:
            await update.message.reply_text("Username @ bilan boshlanishi kerak:")
    
    elif user_id in user_data_store and user_data_store[user_id].get('step') == 'savol_matni':
        user_data_store[user_id]['current_savol'] = {'matn': text}
        user_data_store[user_id]['step'] = 'savol_vaqti'
        await update.message.reply_text(
            f"Savol #{user_data_store[user_id]['savol_nomeri']}:\n"
            f"2. Vaqtni kiriting (soniyada):"
        )
    
    elif user_id in user_data_store and user_data_store[user_id].get('step') == 'savol_vaqti':
        try:
            vaqt = int(text)
            if 1 <= vaqt <= 3600:
                user_data_store[user_id]['current_savol']['vaqt'] = vaqt
                user_data_store[user_id]['step'] = 'javob_turi'
                
                keyboard = [
                    [
                        InlineKeyboardButton("Test variantlari", callback_data='variant'),
                        InlineKeyboardButton("Yozma javob", callback_data='yozma')
                    ]
                ]
                
                await update.message.reply_text(
                    f"Savol #{user_data_store[user_id]['savol_nomeri']}:\n"
                    f"3. Javob turini tanlang:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("Vaqt 1-3600 oralig'ida bo'lishi kerak:")
        except:
            await update.message.reply_text("Son kiriting:")
    
    elif user_id in user_data_store and user_data_store[user_id].get('step') == 'javob_variant':
        user_data_store[user_id]['current_savol']['variantlar'] = text
        user_data_store[user_id]['step'] = 'togri_javob'
        await update.message.reply_text(
            f"Savol #{user_data_store[user_id]['savol_nomeri']}:\n"
            f"4. To'g'ri javob variantini kiriting (A, B, C, D):"
        )
    
    elif user_id in user_data_store and user_data_store[user_id].get('step') == 'togri_javob':
        togri_javob = text.upper()
        savol_nomer = user_data_store[user_id]['savol_nomeri']
        current_savol = user_data_store[user_id]['current_savol']
        
        savol_data = {
            'nomer': savol_nomer,
            'matn': current_savol['matn'],
            'vaqt': current_savol['vaqt'],
            'javob_turi': current_savol.get('javob_turi', 'variant'),
            'togri_javob': togri_javob
        }
        
        if current_savol.get('javob_turi') == 'variant':
            savol_data['variantlar'] = current_savol.get('variantlar', '')
        
        user_data_store[user_id]['savollar'].append(savol_data)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Keyingi savol", callback_data='next_question'),
                InlineKeyboardButton("🏁 Testni tugatish", callback_data='finish_test')
            ]
        ]
        
        await update.message.reply_text(
            f"✅ Savol #{savol_nomer} saqlandi!\n\n"
            f"Test kodi: `{user_data_store[user_id]['current_test_kod']}`\n"
            f"Jami savollar: {savol_nomer}\n\n"
            f"Keyingi amalni tanlang:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        user_data_store[user_id].pop('current_savol', None)
        user_data_store[user_id].pop('step', None)
    
    else:
        await update.message.reply_text(
            "Tushunmadim. /start bilan boshlang yoki test kodini kiriting."
        )

async def send_savol(update, context, user_id, test_kod, savol_nomer):
    test_data = db.get_test(test_kod)
    
    if not test_data or savol_nomer > len(test_data['savollah']):
        await finish_test(update, context, user_id, test_kod)
        return
    
    savol = test_data['savollar'][savol_nomer - 1]
    
    message_text = f"❓ *Savol #{savol_nomer}:*\n{savol['matn']}\n\n"
    
    if savol['javob_turi'] == 'variant' and 'variantlar' in savol:
        message_text += f"{savol['variantlar']}\n\n"
        message_text += f"Javobingizni variant harfi bilan yuboring (A, B, C, D)"
    else:
        message_text += "Javobingizni matn shaklida yuboring"
    
    message_text += f"\n\n⏳ Vaqt: {savol['vaqt']} soniya"
    
    await context.bot.send_message(
        chat_id=user_id,
        text=message_text,
        parse_mode='Markdown'
    )
    
    # Timeout uchun simple solution
    asyncio.create_task(timeout_handler(context, user_id, test_kod, savol_nomer, savol['vaqt']))

async def timeout_handler(context, user_id, test_kod, savol_nomer, vaqt):
    await asyncio.sleep(vaqt)
    
    if user_id in user_sessions and user_sessions[user_id]['test_kod'] == test_kod:
        next_savol = savol_nomer + 1
        test_data = db.get_test(test_kod)
        
        if test_data and next_savol <= len(test_data['savollah']):
            user_sessions[user_id]['current_savol'] = next_savol
            user_data_store[user_id]['current_savol'] = next_savol
            
            await send_savol(None, context, user_id, test_kod, next_savol)
        else:
            await finish_test(None, context, user_id, test_kod)

async def handle_student_answer(update, context, user_id, javob):
    session = db.get_session(user_id)
    if not session:
        await update.message.reply_text("Session tugadi. /start bilan boshlang.")
        return
    
    db.update_session_activity(user_id)
    
    test_kod = session['test_kod']
    current_savol_nomer = session['current_savol']
    
    test_data = db.get_test(test_kod)
    if not test_data or current_savol_nomer > len(test_data['savollah']):
        await update.message.reply_text("Testda xatolik. /start bilan qayta boshlang.")
        db.delete_session(user_id)
        return
    
    savol = test_data['savollar'][current_savol_nomer - 1]
    javob = javob.upper()
    
    # Javobni tekshirish
    if user_id in user_data_store:
        if savol['javob_turi'] == 'variant':
            if javob == savol['togri_javob']:
                user_data_store[user_id]['togri_javoblar'] += 1
                await update.message.reply_text("✅ To'g'ri javob!")
            else:
                await update.message.reply_text(f"❌ Noto'g'ri. To'g'ri javob: {savol['togri_javob']}")
        else:
            if javob.lower() == savol['togri_javob'].lower():
                user_data_store[user_id]['togri_javoblar'] += 1
                await update.message.reply_text("✅ To'g'ri javob!")
            else:
                await update.message.reply_text(f"❌ Noto'g'ri. To'g'ri javob: {savol['togri_javob']}")
    
    # Keyingi savol
    next_savol = current_savol_nomer + 1
    
    if next_savol <= len(test_data['savollah']):
        db.save_session(user_id, test_kod, next_savol)
        user_data_store[user_id]['current_savol'] = next_savol
        
        await send_savol(update, context, user_id, test_kod, next_savol)
    else:
        await finish_test(update, context, user_id, test_kod)

async def finish_test(update, context, user_id, test_kod):
    test_data = db.get_test(test_kod)
    if not test_data:
        return
    
    togri_javoblar = user_data_store.get(user_id, {}).get('togri_javoblar', 0)
    total_savollar = len(test_data['savollah'])
    foiz = (togri_javoblar / total_savollar * 100) if total_savollar > 0 else 0
    
    db.save_result(user_id, test_kod, togri_javoblar, total_savollar)
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"🎉 *Test tugadi!*\n\n"
             f"Test kodi: `{test_kod}`\n"
             f"Jami savollar: {total_savollar} ta\n"
             f"To'g'ri javoblar: {togri_javoblar} ta\n"
             f"Natija: {foiz:.1f}%\n\n"
             f"Yana test ishlash uchun /start bosing.",
        parse_mode='Markdown'
    )
    
    db.delete_session(user_id)
    if user_id in user_data_store:
        del user_data_store[user_id]

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Yordam*\n\n"
        "📌 *Buyruqlar:*\n"
        "/start - Botni ishga tushirish\n"
        "/new_test - Yangi test yaratish (Ustoz)\n"
        "/my_tests - Mening testlarim\n"
        "/help - Yordam\n\n"
        "🤖 *Platforma:* GitHub Actions\n"
        "⏰ *Uptime:* 24/7\n"
        "Isoqov Mironshoh boti"
    )

async def new_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data_store[user_id] = {'step': 'test_kodi'}
    
    await update.message.reply_text(
        "Yangi test yaratish:\n\n"
        "1. Test kodi (5 ta harf/raqam):"
    )

async def my_tests_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_tests = db.get_user_tests(user_id)
    
    if user_tests:
        tests_info = "📋 *Siz yaratgan testlar:*\n\n"
        for test in user_tests:
            test_kod = [k for k, v in tests_db.items() if v == test][0]
            tests_info += f"🔹 *Test kodi:* `{test_kod}`\n"
            tests_info += f"   ❓ Savollar: {len(test['savollah'])} ta\n"
            tests_info += "   ────────────────\n"
        
        await update.message.reply_text(tests_info, parse_mode='Markdown')
    else:
        await update.message.reply_text("Siz hali test yaratmagansiz.")

def main():
    print("✅ Bot GitHub Actions uchun moslandi!")
    print(f"📊 Memory Database: {len(tests_db)} test")
    print(f"👥 Faol foydalanuvchilar: {len(user_sessions)}")
    
    # Botni ishga tushirish
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new_test", new_test_command))
    app.add_handler(CommandHandler("my_tests", my_tests_command))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 Bot ishga tushmoqda...")
    app.run_polling()

if __name__ == '__main__':
    main()
