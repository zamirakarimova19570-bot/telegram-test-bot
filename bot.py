from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import os
import logging

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot tokeni (GitHub Secrets dan)
TOKEN = os.getenv('BOT_TOKEN', '8587222975:AAEq18hC7QrRF1UsNv88JX4q9enU4iCvXTw')

# Test ma'lumotlari
tests_db = {
    'MAT1': {
        'name': 'Matematika testi',
        'questions': [
            {'q': '2 + 2 = ?', 'options': ['3', '4', '5', '6'], 'answer': 'B'},
            {'q': '5 × 3 = ?', 'options': ['10', '15', '20', '25'], 'answer': 'B'},
            {'q': '12 ÷ 4 = ?', 'options': ['2', '3', '4', '6'], 'answer': 'B'},
        ]
    },
    'ENG2': {
        'name': 'Ingliz tili testi',
        'questions': [
            {'q': "Apple - ?", 'options': ['Olma', 'Nok', 'Banan', 'Uzum'], 'answer': 'A'},
            {'q': "Book - ?", 'options': ['Daftar', 'Kitob', 'Qalam', 'Ruchka'], 'answer': 'B'},
            {'q': "Teacher - ?", 'options': ['O‘quvchi', 'O‘qituvchi', 'Doktor', 'Muhandis'], 'answer': 'B'},
        ]
    },
    'HIS3': {
        'name': 'Tarix testi',
        'questions': [
            {'q': "O'zbekiston poytaxti?", 'options': ['Toshkent', 'Samarqand', 'Buxoro', 'Andijon'], 'answer': 'A'},
            {'q': "Mustaqillik yili?", 'options': ['1990', '1991', '1992', '1993'], 'answer': 'B'},
        ]
    }
}

# Foydalanuvchi sessionlari
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    keyboard = [
        [InlineKeyboardButton("📚 Test ishlash", callback_data='start_test')],
        [InlineKeyboardButton("📊 Natijalarim", callback_data='my_results')],
        [InlineKeyboardButton("ℹ️ Bot haqida", callback_data='about')]
    ]
    
    await update.message.reply_text(
        f"👋 Salom, {update.message.from_user.first_name}!\n\n"
        f"🤖 *GitHub Actions Test Bot*\n"
        f"📍 Server: GitHub Actions\n"
        f"⏰ Uptime: 24/7\n"
        f"💰 Narx: BEPUL\n"
        f"🔧 Platforma: GitHub.com\n\n"
        f"Test ishlash uchun quyidagi tugmalardan foydalaning:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'start_test':
        keyboard = []
        for test_code, test_info in tests_db.items():
            keyboard.append([InlineKeyboardButton(
                f"{test_code} - {test_info['name']} ({len(test_info['questions'])} savol)",
                callback_data=f'select_{test_code}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data='back_main')])
        
        await query.edit_message_text(
            "📚 *Mavjud testlar:*\n\n"
            "Quyidagi testlardan birini tanlang:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data.startswith('select_'):
        test_code = query.data.replace('select_', '')
        test_info = tests_db[test_code]
        
        # Session yaratish
        user_sessions[user_id] = {
            'test_code': test_code,
            'current': 0,
            'score': 0,
            'answers': []
        }
        
        # Birinchi savolni yuborish
        await send_question(query, context, user_id)
    
    elif query.data == 'my_results':
        if user_id in user_sessions and user_sessions[user_id]['answers']:
            session = user_sessions[user_id]
            test_info = tests_db[session['test_code']]
            score = session['score']
            total = len(test_info['questions'])
            
            await query.edit_message_text(
                f"📊 *Sizning natijangiz:*\n\n"
                f"Test: {test_info['name']}\n"
                f"To'g'ri javoblar: {score}/{total}\n"
                f"Foiz: {(score/total*100):.1f}%\n\n"
                f"Yana test ishlash uchun:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Test ishlash", callback_data='start_test')],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data='back_main')]
                ])
            )
        else:
            await query.edit_message_text(
                "📭 Siz hali test ishlamagansiz.\n"
                "Birinchi test ishlang!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Test ishlash", callback_data='start_test')],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data='back_main')]
                ])
            )
    
    elif query.data == 'about':
        await query.edit_message_text(
            "🤖 *Bot haqida:*\n\n"
            "• Platforma: GitHub Actions\n"
            "• Uptime: 24/7 (avtomatik restart)\n"
            "• Narx: Umrbod bepul\n"
            "• Kod: Open source\n"
            "• Dasturlash tili: Python\n"
            "• Kutubxona: python-telegram-bot\n\n"
            "📍 GitHub: github.com/username/telegram-test-bot",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Bosh menyu", callback_data='back_main')]
            ])
        )
    
    elif query.data == 'back_main':
        keyboard = [
            [InlineKeyboardButton("📚 Test ishlash", callback_data='start_test')],
            [InlineKeyboardButton("📊 Natijalarim", callback_data='my_results')],
            [InlineKeyboardButton("ℹ️ Bot haqida", callback_data='about')]
        ]
        
        await query.edit_message_text(
            "🏠 *Bosh menyu*\n\n"
            "Quyidagi tugmalardan birini tanlang:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def send_question(query, context, user_id):
    session = user_sessions[user_id]
    test_code = session['test_code']
    question_num = session['current']
    
    test_info = tests_db[test_code]
    question = test_info['questions'][question_num]
    
    # Variantlar tugmalari
    keyboard = []
    options = ['A', 'B', 'C', 'D']
    
    for i, option_text in enumerate(question['options']):
        if i < len(options):
            keyboard.append([InlineKeyboardButton(
                f"{options[i]}) {option_text}",
                callback_data=f"ans_{options[i]}"
            )])
    
    await query.edit_message_text(
        f"📝 *Test: {test_info['name']}*\n"
        f"❓ Savol {question_num + 1}/{len(test_info['questions'])}:\n\n"
        f"{question['q']}\n\n"
        f"Javobingizni tanlang:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id not in user_sessions:
        await query.edit_message_text(
            "⏳ Sessiya muddati tugagan.\n"
            "Yangi test boshlang.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Yangi test", callback_data='start_test')]
            ])
        )
        return
    
    selected_answer = query.data.replace('ans_', '')
    session = user_sessions[user_id]
    test_code = session['test_code']
    question_num = session['current']
    
    test_info = tests_db[test_code]
    question = test_info['questions'][question_num]
    
    # Javobni tekshirish
    is_correct = selected_answer == question['answer']
    
    if is_correct:
        session['score'] += 1
        result_text = "✅ *To'g'ri javob!*"
    else:
        result_text = f"❌ *Noto'g'ri.* To'g'ri javob: {question['answer']})"
    
    # Javobni saqlash
    session['answers'].append({
        'question': question['q'],
        'user_answer': selected_answer,
        'correct': question['answer'],
        'is_correct': is_correct
    })
    
    # Keyingi savol
    session['current'] += 1
    
    if session['current'] < len(test_info['questions']):
        await query.edit_message_text(
            f"{result_text}\n\n"
            f"Keyingi savolga o'tilmoqda...",
            parse_mode='Markdown'
        )
        # 2 soniya kutib, keyingi savol
        import asyncio
        await asyncio.sleep(2)
        await send_question(query, context, user_id)
    else:
        # Test tugadi
        score = session['score']
        total = len(test_info['questions'])
        
        await query.edit_message_text(
            f"🎉 *Test tugadi!*\n\n"
            f"Test: {test_info['name']}\n"
            f"To'g'ri javoblar: {score}/{total}\n"
            f"Natija: {(score/total*100):.1f}%\n\n"
            f"Yana test ishlash uchun:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Yangi test", callback_data='start_test')],
                [InlineKeyboardButton("📊 Natijalarim", callback_data='my_results')],
                [InlineKeyboardButton("🏠 Bosh menyu", callback_data='back_main')]
            ])
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Yordam*\n\n"
        "📌 *Buyruqlar:*\n"
        "/start - Botni ishga tushirish\n"
        "/test - Test ishlash\n"
        "/results - Natijalarni ko'rish\n"
        "/help - Yordam\n"
        "/about - Bot haqida\n\n"
        "🤖 *Platforma:* GitHub Actions\n"
        "⏰ *Uptime:* 24/7\n"
        "💰 *Narx:* Bepul\n\n"
        "GitHub: github.com/username/telegram-test-bot"
    )

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📚 Testlar ro'yxati", callback_data='start_test')]]
    
    await update.message.reply_text(
        "Test ishlash uchun quyidagi tugmani bosing:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def results_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id in user_sessions and user_sessions[user_id]['answers']:
        session = user_sessions[user_id]
        test_info = tests_db[session['test_code']]
        score = session['score']
        total = len(test_info['questions'])
        
        await update.message.reply_text(
            f"📊 *Sizning natijangiz:*\n\n"
            f"Test: {test_info['name']}\n"
            f"To'g'ri javoblar: {score}/{total}\n"
            f"Foiz: {(score/total*100):.1f}%\n\n"
            f"Yana test ishlash uchun /test"
        )
    else:
        await update.message.reply_text(
            "📭 Siz hali test ishlamagansiz.\n"
            "Test ishlash uchun /test buyrug'ini ishlating."
        )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *GitHub Actions Telegram Bot*\n\n"
        "✅ 24/7 ishlaydi\n"
        "✅ Bepul hosting\n"
        "✅ Avtomatik restart\n"
        "✅ Open source\n\n"
        "📍 GitHub: github.com/username/telegram-test-bot\n"
        "🔧 Platforma: GitHub Actions\n"
        "💻 Dasturlash: Python"
    )

def main():
    print("🚀 GitHub Actions da bot ishga tushmoqda...")
    print("🤖 Platforma: GitHub")
    print("⏰ Uptime: 24/7")
    print("💰 Narx: BEPUL")
    
    # Botni ishga tushirish
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CommandHandler("results", results_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Callback handlerlar
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^(start_test|my_results|about|back_main|select_)'))
    application.add_handler(CallbackQueryHandler(answer_handler, pattern='^ans_'))
    
    # Text message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
        lambda update, context: update.message.reply_text(
            "Botni ishga tushirish uchun /start buyrug'ini ishlating."
        )
    ))
    
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    print("📍 Token:", "***" + TOKEN[-4:] if len(TOKEN) > 4 else "***")
    
    # Botni ishga tushirish
    application.run_polling()

if __name__ == '__main__':
    main()
