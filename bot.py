from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
import asyncio
import re
from datetime import datetime
import time
import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Konstantsalar
TEST_KOD_UZUNLIGI = 5
MAX_SAVOL_SONI = 50
SESSION_TIMEOUT = 300  # 5 minut
MAX_USERS = 10000  # Maksimum foydalanuvchi soni

# Holatlar (States)
(
    MENU, USTOZ_USERNAME, TEST_KODI, 
    SAVOL_MATNI, SAVOL_VAQTI, JAVOB_TURI, 
    JAVOB_MATNI, TOGR_JAVOB, TEST_KOD_KIRITISH
) = range(9)

# Database class
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('test_bot.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            test_kod TEXT PRIMARY KEY,
            ustoz_id INTEGER,
            ustoz_username TEXT,
            savollar TEXT,
            yaratilgan_vaqt TIMESTAMP,
            status TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            test_kod TEXT,
            togri_javoblar INTEGER,
            total_savollar INTEGER,
            natija REAL,
            yakunlangan_vaqt TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            user_id INTEGER PRIMARY KEY,
            test_kod TEXT,
            current_savol INTEGER,
            last_activity TIMESTAMP,
            status TEXT
        )
        ''')
        
        self.conn.commit()
    
    def save_test(self, test_kod: str, ustoz_id: int, ustoz_username: str, savollar: list):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO tests 
        (test_kod, ustoz_id, ustoz_username, savollar, yaratilgan_vaqt, status)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            test_kod, ustoz_id, ustoz_username, 
            json.dumps(savollar, ensure_ascii=False),
            datetime.now().isoformat(),
            'active'
        ))
        self.conn.commit()
    
    def get_test(self, test_kod: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tests WHERE test_kod = ?', (test_kod,))
        row = cursor.fetchone()
        if row:
            return {
                'test_kod': row[0],
                'ustoz_id': row[1],
                'ustoz_username': row[2],
                'savollar': json.loads(row[3]),
                'yaratilgan_vaqt': row[4],
                'status': row[5]
            }
        return None
    
    def save_session(self, user_id: int, test_kod: str, current_savol: int):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO sessions 
        (user_id, test_kod, current_savol, last_activity, status)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id, test_kod, current_savol,
            datetime.now().isoformat(),
            'active'
        ))
        self.conn.commit()
    
    def get_session(self, user_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM sessions WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                'user_id': row[0],
                'test_kod': row[1],
                'current_savol': row[2],
                'last_activity': row[3],
                'status': row[4]
            }
        return None
    
    def update_session_activity(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE sessions SET last_activity = ? WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        self.conn.commit()
    
    def delete_session(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def save_result(self, user_id: int, test_kod: str, togri_javoblar: int, total_savollar: int):
        natija = (togri_javoblar / total_savollar * 100) if total_savollar > 0 else 0
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO results 
        (user_id, test_kod, togri_javoblar, total_savollar, natija, yakunlangan_vaqt)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id, test_kod, togri_javoblar, total_savollar,
            natija, datetime.now().isoformat()
        ))
        self.conn.commit()
    
    def get_user_tests(self, ustoz_id: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tests WHERE ustoz_id = ? ORDER BY yaratilgan_vaqt DESC', (ustoz_id,))
        tests = []
        for row in cursor.fetchall():
            tests.append({
                'test_kod': row[0],
                'ustoz_id': row[1],
                'ustoz_username': row[2],
                'savollar': json.loads(row[3]),
                'yaratilgan_vaqt': row[4],
                'status': row[5]
            })
        return tests
    
    def close(self):
        self.conn.close()

# Global obyektlar
db = Database()
active_jobs = {}  # user_id -> job

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
        f"• Maksimum foydalanuvchi: {MAX_USERS}\n"
        "• Har bir test uchun: 5 ta belgili kod\n"
        "• Maksimum savol: 50 ta\n\n"
        "⚠️ *Eslatma:* Agar foydalanuvchi boshqa ilovaga o'tsa, test avtomatik to'xtaydi!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == 'oquvchi':
        context.user_data['role'] = 'oquvchi'
        await query.edit_message_text(
            "Test kodini kiriting (5 ta harf/raqam):\n\n"
            "Namuna: ABC12 yoki 123DE\n\n"
            "Bekor qilish uchun /cancel"
        )
        return TEST_KOD_KIRITISH
    
    elif data == 'ustoz':
        context.user_data['role'] = 'ustoz'
        await query.edit_message_text(
            "Ustoz username kiriting (@ bilan):\n\n"
            "Namuna: @username\n\n"
            "Bekor qilish uchun /cancel"
        )
        return USTOZ_USERNAME
    
    elif data == 'my_tests':
        user_tests = db.get_user_tests(user_id)
        if user_tests:
            tests_info = "📋 *Siz yaratgan testlar:*\n\n"
            for test in user_tests:
                tests_info += f"🔹 *Test kodi:* `{test['test_kod']}`\n"
                tests_info += f"   📅 {test['yaratilgan_vaqt'][:16]}\n"
                tests_info += f"   ❓ Savollar: {len(test['savollar'])} ta\n"
                tests_info += "   ────────────────\n"
            
            await query.edit_message_text(
                f"{tests_info}\n"
                f"Yangi test yaratish uchun 'Ustoz' ni tanlang.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👨‍🏫 Yangi test", callback_data='ustoz')],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data='menu')]
                ])
            )
        else:
            await query.edit_message_text(
                "Siz hali hech qanday test yaratmagansiz.\n\n"
                "Yangi test yaratish uchun 'Ustoz' ni tanlang.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👨‍🏫 Yangi test", callback_data='ustoz')],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data='menu')]
                ])
            )
        return MENU
    
    elif data == 'menu':
        await query.edit_message_text(
            "Bosh menyu:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👨‍🎓 O'quvchi", callback_data='oquvchi')],
                [InlineKeyboardButton("👨‍🏫 Ustoz", callback_data='ustoz')],
                [InlineKeyboardButton("📋 Yaratilgan testlar", callback_data='my_tests')]
            ])
        )
        return MENU
    
    elif data == 'next_question':
        if 'current_test_kod' in context.user_data:
            test_kod = context.user_data['current_test_kod']
            current_number = context.user_data.get('savol_nomeri', 1)
            context.user_data['savol_nomeri'] = current_number + 1
            
            if current_number + 1 <= MAX_SAVOL_SONI:
                await query.edit_message_text(
                    f"Savol #{current_number + 1}:\n"
                    f"1. Savol matnini kiriting:\n\n"
                    f"Bekor qilish uchun /cancel"
                )
                return SAVOL_MATNI
            else:
                await query.edit_message_text(
                    f"✅ Maksimum {MAX_SAVOL_SONI} ta savol qo'shildi!\n"
                    f"Test kodi: `{test_kod}`\n"
                    f"Testni o'quvchilarga tarqatishingiz mumkin.\n\n"
                    f"/start - Bosh menyuga qaytish",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
    
    elif data == 'finish_test':
        if 'current_test_kod' in context.user_data:
            test_kod = context.user_data['current_test_kod']
            
            # Savollarni saqlash
            if 'savollar' in context.user_data:
                ustoz_username = context.user_data.get('ustoz_username', '')
                db.save_test(
                    test_kod, 
                    user_id, 
                    ustoz_username, 
                    context.user_data['savollar']
                )
            
            savollar_soni = len(context.user_data.get('savollar', []))
            
            await query.edit_message_text(
                f"✅ Test muvaffaqiyatli yaratildi!\n\n"
                f"📊 *Test ma'lumotlari:*\n"
                f"• Test kodi: `{test_kod}`\n"
                f"• Savollar soni: {savollar_soni} ta\n"
                f"• Yaratilgan vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                f"Testni o'quvchilarga tarqatishingiz mumkin.\n\n"
                f"/start - Yangi test yaratish",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    
    elif data == 'variant' or data == 'yozma':
        context.user_data['current_savol']['javob_turi'] = data
        if data == 'variant':
            await query.edit_message_text(
                f"Savol #{context.user_data['savol_nomeri']}:\n"
                f"4. Variantlarni kiriting (har bir variant yangi qatorda):\n\n"
                f"Masalan:\n"
                f"A) Olma\n"
                f"B) Nok\n"
                f"C) Banan\n"
                f"D) Apelsin\n\n"
                f"Bekor qilish uchun /cancel"
            )
            return JAVOB_MATNI
        else:  # yozma
            await query.edit_message_text(
                f"Savol #{context.user_data['savol_nomeri']}:\n"
                f"4. To'g'ri javobni kiriting (faqat bot ko'radi):\n\n"
                f"Bekor qilish uchun /cancel"
            )
            return TOGR_JAVOB
    
    elif data == 'retry_question':
        await query.edit_message_text(
            f"Savol #{context.user_data['savol_nomeri']}:\n"
            f"1. Savol matnini kiriting:\n\n"
            f"Bekor qilish uchun /cancel"
        )
        return SAVOL_MATNI

async def handle_ustoz_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    user_id = update.message.from_user.id
    
    if not username.startswith('@'):
        await update.message.reply_text(
            "❌ Iltimos, username @ bilan boshlansin. Qayta kiriting:\n\n"
            "Bekor qilish uchun /cancel"
        )
        return USTOZ_USERNAME
    
    await update.message.reply_text(
        f"✅ Ustoz username qabul qilindi: {username}\n"
        f"Kiritganingiz uchun raxmat!\n\n"
        f"Endi test kodi yaratishingiz kerak. Test kodi {TEST_KOD_UZUNLIGI} ta harf/raqamdan iborat bo'lsin.\n\n"
        f"Test kodini kiriting:\n\n"
        f"Bekor qilish uchun /cancel"
    )
    
    context.user_data['ustoz_username'] = username
    return TEST_KODI

async def handle_test_kodi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    test_kod = update.message.text.strip().upper()
    user_id = update.message.from_user.id
    
    if len(test_kod) != TEST_KOD_UZUNLIGI or not re.match(r'^[A-Za-z0-9]+$', test_kod):
        await update.message.reply_text(
            f"❌ Noto'g'ri format! Test kodi {TEST_KOD_UZUNLIGI} ta harf/raqamdan iborat bo'lishi kerak.\n"
            f"Qayta kiriting:\n\n"
            f"Bekor qilish uchun /cancel"
        )
        return TEST_KODI
    
    if db.get_test(test_kod):
        await update.message.reply_text(
            "❌ Bu test kodi allaqachon band. Boshqa kod kiriting:\n\n"
            "Bekor qilish uchun /cancel"
        )
        return TEST_KODI
    
    context.user_data['current_test_kod'] = test_kod
    context.user_data['savol_nomeri'] = 1
    context.user_data['savollar'] = []
    
    await update.message.reply_text(
        f"✅ Test kodi yaratildi: `{test_kod}`\n\n"
        f"Endi savollar yaratishingiz mumkin (maksimum {MAX_SAVOL_SONI} ta).\n\n"
        f"Savol #{context.user_data['savol_nomeri']}:\n"
        f"1. Savol matnini kiriting:\n\n"
        f"Bekor qilish uchun /cancel",
        parse_mode='Markdown'
    )
    
    return SAVOL_MATNI

async def handle_savol_matni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    savol_matn = update.message.text.strip()
    
    if 'current_savol' not in context.user_data:
        context.user_data['current_savol'] = {}
    
    context.user_data['current_savol']['matn'] = savol_matn
    context.user_data['current_savol']['nomer'] = context.user_data['savol_nomeri']
    
    await update.message.reply_text(
        f"Savol #{context.user_data['savol_nomeri']}:\n"
        f"2. Savol uchun vaqt kiriting (soniyalarda, masalan: 60):\n\n"
        f"Bekor qilish uchun /cancel"
    )
    
    return SAVOL_VAQTI

async def handle_savol_vaqti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        vaqt = int(update.message.text.strip())
        if vaqt <= 0 or vaqt > 3600:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Noto'g'ri vaqt! 1-3600 soniyalar oralig'ida butun son kiriting:\n\n"
            "Bekor qilish uchun /cancel"
        )
        return SAVOL_VAQTI
    
    context.user_data['current_savol']['vaqt'] = vaqt
    
    keyboard = [
        [
            InlineKeyboardButton("A) Test variantlari", callback_data='variant'),
            InlineKeyboardButton("B) Yozma javob", callback_data='yozma')
        ],
        [InlineKeyboardButton("🔙 Savolni qaytadan", callback_data='retry_question')]
    ]
    
    await update.message.reply_text(
        f"Savol #{context.user_data['savol_nomeri']}:\n"
        f"3. Javob turini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return JAVOB_TURI

async def handle_javob_matni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    javob_matn = update.message.text.strip()
    context.user_data['current_savol']['javob_matn'] = javob_matn
    
    await update.message.reply_text(
        f"Savol #{context.user_data['savol_nomeri']}:\n"
        f"5. To'g'ri javob variantini kiriting (A, B, C, D):\n\n"
        f"Bekor qilish uchun /cancel"
    )
    
    return TOGR_JAVOB

async def handle_togri_javob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    togri_javob = update.message.text.strip().upper()
    test_kod = context.user_data['current_test_kod']
    savol_nomer = context.user_data['savol_nomeri']
    
    current_savol = context.user_data['current_savol']
    savol_data = {
        'nomer': savol_nomer,
        'matn': current_savol['matn'],
        'vaqt': current_savol['vaqt'],
        'javob_turi': current_savol['javob_turi'],
        'togri_javob': togri_javob
    }
    
    if current_savol['javob_turi'] == 'variant':
        savol_data['variantlar'] = current_savol.get('javob_matn', '')
    
    if 'savollar' not in context.user_data:
        context.user_data['savollar'] = []
    context.user_data['savollar'].append(savol_data)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Keyingi savol", callback_data='next_question'),
            InlineKeyboardButton("🏁 Testni tugatish", callback_data='finish_test')
        ]
    ]
    
    await update.message.reply_text(
        f"✅ Savol #{savol_nomer} saqlandi!\n\n"
        f"Test kodi: `{test_kod}`\n"
        f"Jami savollar: {savol_nomer} ta\n\n"
        f"Keyingi amalni tanlang:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Menu holatiga qaytamiz
    return MENU

async def handle_test_kod_kiritish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    test_kod = update.message.text.strip().upper()
    user_id = update.message.from_user.id
    
    test_data = db.get_test(test_kod)
    if not test_data:
        await update.message.reply_text(
            "❌ Bunday test kodi topilmadi. Qayta kiriting:\n\n"
            "Bekor qilish uchun /cancel"
        )
        return TEST_KOD_KIRITISH
    
    if len(test_data['savollar']) == 0:
        await update.message.reply_text(
            "❌ Bu testda savollar mavjud emas. Boshqa test kodini kiriting:\n\n"
            "Bekor qilish uchun /cancel"
        )
        return TEST_KOD_KIRITISH
    
    db.save_session(user_id, test_kod, 1)
    
    context.user_data['test_kod'] = test_kod
    context.user_data['current_savol'] = 1
    context.user_data['togri_javoblar'] = 0
    
    await send_savol_to_user(update, context, user_id, test_kod, 1)
    
    return ConversationHandler.END

async def send_savol_to_user(update, context, user_id, test_kod, savol_nomer):
    test_data = db.get_test(test_kod)
    
    if not test_data or savol_nomer > len(test_data['savollar']):
        await finish_test_for_user(update, context, user_id, test_kod)
        return
    
    savol = test_data['savollar'][savol_nomer - 1]
    
    message_text = f"❓ *Savol #{savol_nomer}:*\n{savol['matn']}\n\n"
    
    if savol['javob_turi'] == 'variant' and 'variantlar' in savol:
        message_text += f"{savol['variantlar']}\n\n"
        message_text += f"Javobingizni variant harfi bilan yuboring (A, B, C, D)"
    else:
        message_text += "Javobingizni matn shaklida yuboring"
    
    message_text += f"\n\n⏳ Vaqt: {savol['vaqt']} soniya"
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='Markdown'
        )
        
        db.save_session(user_id, test_kod, savol_nomer)
        
        if user_id in active_jobs:
            try:
                active_jobs[user_id].schedule_removal()
            except:
                pass
        
        job = context.job_queue.run_once(
            lambda ctx: time_out_savol(ctx, user_id, test_kod, savol_nomer),
            savol['vaqt']
        )
        active_jobs[user_id] = job
        
    except Exception as e:
        logger.error(f"Savol yuborishda xatolik: {e}")

async def time_out_savol(context: ContextTypes.DEFAULT_TYPE, user_id, test_kod, savol_nomer):
    try:
        next_savol_nomer = savol_nomer + 1
        test_data = db.get_test(test_kod)
        
        if test_data and next_savol_nomer <= len(test_data['savollar']):
            db.save_session(user_id, test_kod, next_savol_nomer)
            await send_savol_to_user(None, context, user_id, test_kod, next_savol_nomer)
        else:
            await finish_test_for_user(None, context, user_id, test_kod)
    except Exception as e:
        logger.error(f"Timeout xatosi: {e}")

async def finish_test_for_user(update, context, user_id, test_kod):
    try:
        session = db.get_session(user_id)
        if not session:
            return
        
        test_data = db.get_test(test_kod)
        if not test_data:
            return
        
        togri_javoblar = context.user_data.get('togri_javoblar', 0) if context.user_data else 0
        total_savollar = len(test_data['savollar'])
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
        
        if user_id in active_jobs:
            try:
                active_jobs[user_id].schedule_removal()
            except:
                pass
            del active_jobs[user_id]
            
    except Exception as e:
        logger.error(f"Testni tugatishda xatolik: {e}")

async def handle_student_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    javob = update.message.text.strip().upper()
    
    session = db.get_session(user_id)
    if not session:
        await update.message.reply_text(
            "Siz hozir testda emassiz. Test ishlash uchun /start ni bosing."
        )
        return
    
    db.update_session_activity(user_id)
    
    test_kod = session['test_kod']
    current_savol_nomer = session['current_savol']
    
    test_data = db.get_test(test_kod)
    if not test_data or current_savol_nomer > len(test_data['savollar']):
        await update.message.reply_text("Testda xatolik. /start bilan qayta boshlang.")
        db.delete_session(user_id)
        return
    
    savol = test_data['savollar'][current_savol_nomer - 1]
    
    if savol['javob_turi'] == 'variant':
        if javob == savol['togri_javob']:
            context.user_data['togri_javoblar'] = context.user_data.get('togri_javoblar', 0) + 1
            await update.message.reply_text("✅ To'g'ri javob!")
        else:
            await update.message.reply_text(f"❌ Noto'g'ri. To'g'ri javob: {savol['togri_javob']}")
    else:
        if javob.lower() == savol['togri_javob'].lower():
            context.user_data['togri_javoblar'] = context.user_data.get('togri_javoblar', 0) + 1
            await update.message.reply_text("✅ To'g'ri javob!")
        else:
            await update.message.reply_text(f"❌ Noto'g'ri. To'g'ri javob: {savol['togri_javob']}")
    
    next_savol_nomer = current_savol_nomer + 1
    
    if next_savol_nomer <= len(test_data['savollar']):
        if user_id in active_jobs:
            try:
                active_jobs[user_id].schedule_removal()
            except:
                pass
        
        await send_savol_to_user(update, context, user_id, test_kod, next_savol_nomer)
    else:
        await finish_test_for_user(update, context, user_id, test_kod)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if 'current_test_kod' in context.user_data and 'savollar' in context.user_data:
        test_kod = context.user_data['current_test_kod']
        ustoz_username = context.user_data.get('ustoz_username', '')
        
        db.save_test(
            test_kod, 
            user_id, 
            ustoz_username, 
            context.user_data['savollar']
        )
    
    db.delete_session(user_id)
    
    if user_id in active_jobs:
        try:
            active_jobs[user_id].schedule_removal()
        except:
            pass
        del active_jobs[user_id]
    
    if context.user_data:
        context.user_data.clear()
    
    await update.message.reply_text(
        "Amallar bekor qilindi. Yangi test uchun /start ni bosing."
    )
    return ConversationHandler.END

async def monitor_sessions(context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("Monitoring ishlayapti...")
    except Exception as e:
        logger.error(f"Monitoring xatosi: {e}")

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alohida callback query handler"""
    query = update.callback_query
    await query.answer()
    
    # Boshqa callback'larni qayta ishlash
    if query.data in ['next_question', 'finish_test']:
        await button_handler(update, context)

def main():
    TOKEN = "8587222975:AAEq18hC7QrRF1UsNv88JX4q9enU4iCvXTw"
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("boshlash", start)
        ],
        states={
            MENU: [
                CallbackQueryHandler(button_handler, pattern='^(oquvchi|ustoz|my_tests|menu)$')
            ],
            USTOZ_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ustoz_username)
            ],
            TEST_KODI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_test_kodi)
            ],
            SAVOL_MATNI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_savol_matni)
            ],
            SAVOL_VAQTI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_savol_vaqti)
            ],
            JAVOB_TURI: [
                CallbackQueryHandler(button_handler, pattern='^(variant|yozma|retry_question)$')
            ],
            JAVOB_MATNI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_javob_matni)
            ],
            TOGR_JAVOB: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_togri_javob)
            ],
            TEST_KOD_KIRITISH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_test_kod_kiritish)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start)
        ],
        allow_reentry=True
    )
    
    # Alohida callback handler
    app.add_handler(CallbackQueryHandler(
        callback_query_handler,
        pattern='^(next_question|finish_test)$'
    ))
    
    app.add_handler(conv_handler)
    
    # O'quvchi javoblari uchun handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_student_answer))
    
    app.job_queue.run_repeating(monitor_sessions, interval=60, first=10)
    
    print("🤖 Bot ishga tushdi...")
    print(f"📊 Maksimum foydalanuvchi soni: {MAX_USERS}")
    print("📁 Database: test_bot.db")
    
    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\nBot to'xtatildi.")
    finally:
        db.close()

if __name__ == '__main__':
    main()
