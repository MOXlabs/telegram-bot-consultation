import os
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask
import threading

# Создаем Flask app для веб-сервера
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот для консультаций работает! " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
NAME, CONTACT, PROBLEM, DATETIME, CONFIRM = range(5)

# Настройка московского времени
def get_moscow_time():
    utc_now = datetime.utcnow()
    moscow_time = utc_now + timedelta(hours=3)
    return moscow_time

def format_moscow_time():
    return get_moscow_time().strftime('%d.%m.%Y %H:%M:%S (МСК)')

# Данные бота
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8257818553:AAFNSfYB7L9gqg285lssp6x9djn1nBsDxgE')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '744451342')

WELCOME_PHOTO_URL = "https://i.ibb.co/yFdZ673f/Advocate.jpg"
SUCCESS_PHOTO_URL = "https://i.ibb.co/PGSnbR2G/Advocate-Finalact.jpg"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    context.user_data['first_click'] = True

    try:
        await update.message.reply_photo(
            photo=WELCOME_PHOTO_URL,
            caption="👋 Привет, я Арина - бот адвоката Алексея Мельникова. Я помогу Вам записаться на консультацию"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await update.message.reply_text(
            "👋 Привет, я Арина - бот адвоката Алексея Мельникова. Я помогу Вам записаться на консультацию"
        )

    keyboard = [[KeyboardButton("📝 Записаться на консультацию")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Нажмите кнопку ниже, чтобы начать заполнение заявки:",
        reply_markup=reply_markup
    )

async def handle_application_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    is_first_click = context.user_data.get('first_click', True)

    if is_first_click:
        context.user_data['first_click'] = False
        await update.message.reply_text(
            "Отлично! Давайте заполним заявку на консультацию.\n\n📝 Как к вам обращаться? (ФИО или имя)",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        try:
            await update.message.reply_photo(
                photo=WELCOME_PHOTO_URL,
                caption="👋 Привет, я Арина - бот адвоката Алексея Мельникова. Я помогу Вам записаться на консультацию"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            await update.message.reply_text("👋 Привет, я Арина - бот адвоката Алексея Мельникова. Я помогу Вам записаться на консультацию")

        await update.message.reply_text(
            "📝 Как к вам обращаться? (ФИО или имя)",
            reply_markup=ReplyKeyboardRemove()
        )

    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    context.user_data['name'] = update.message.text
    await update.message.reply_text("📞 Укажите ваш номер телефона или другой способ связи (Telegram, WhatsApp и т.д.):")
    return CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    context.user_data['contact'] = update.message.text
    await update.message.reply_text("❓ Кратко опишите суть проблемы (чтобы понимать, с чем мы будем работать):")
    return PROBLEM

async def get_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    context.user_data['problem'] = update.message.text
    await update.message.reply_text("📅 Укажите желаемые дату и время для консультации:\n\n"
        "Например: '25 декабря 15:30' или 'завтра в 18:00'")
    return DATETIME

async def get_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    context.user_data['datetime'] = update.message.text

    name = context.user_data.get('name', '')
    contact = context.user_data.get('contact', '')
    problem = context.user_data.get('problem', '')

    summary = f"""📋 Проверьте вашу заявку:

👤 Имя: {name}
📞 Контакт: {contact}
❓ Проблема: {problem}
📅 Желаемое время: {update.message.text}

Всё верно?"""

    keyboard = [['✅ Да, отправить', '❌ Нет, заполнить заново']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(summary, reply_markup=reply_markup)
    return CONFIRM

async def confirm_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    user_choice = update.message.text

    if user_choice == '✅ Да, отправить':
        await send_application_to_admin(update, context)
        context.user_data['first_click'] = False

        # Отправляем фото с сообщением об успешной записи
        await update.message.reply_photo(
            photo=SUCCESS_PHOTO_URL,
            caption="✅ Спасибо! Ваша заявка отправлена. Мы свяжемся с вами в ближайшее время!"
        )

        keyboard = [[KeyboardButton("📝 Записаться на консультацию")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "Нажмите кнопку ниже, чтобы начать заполнение новой заявки:",
            reply_markup=reply_markup
        )

        # Очищаем данные анкеты
        for key in ['name', 'contact', 'problem', 'datetime']:
            if key in context.user_data:
                del context.user_data[key]

        return ConversationHandler.END
    
    else:
        await update.message.reply_text(
            "🔄 Давайте заполним заявку заново.",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text("Отлично! Давайте заполним заявку на консультацию.\n\n📝 Как к вам обращаться? (ФИО или имя)")
        return NAME

async def send_application_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    user_data = context.user_data
    user = update.message.from_user

    application_text = f"""🚨 НОВАЯ ЗАЯВКА НА КОНСУЛЬТАЦИЮ

👤 Клиент: {user_data.get('name', '')}
📞 Контакт: {user_data.get('contact', '')}
❓ Проблема: {user_data.get('problem', '')}
📅 Желаемое время: {user_data.get('datetime', '')}

📊 Информация о пользователе:
Username: @{user.username if user.username else 'не указан'}
Полное имя: {user.first_name} {user.last_name or ''}

⏰ Время заявки: {format_moscow_time()}"""

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=application_text
        )
        logger.info("✅ Заявка отправлена администратору")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки заявки: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    context.user_data['first_click'] = False
    keyboard = [[KeyboardButton("📝 Записаться на консультацию")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        '❌ Заявка отменена. Если захотите записаться, нажмите кнопку:',
        reply_markup=reply_markup
    )

    # Очищаем данные анкеты
    for key in ['name', 'contact', 'problem', 'datetime']:
        if key in context.user_data:
            del context.user_data[key]

    return ConversationHandler.END

def run_bot():
    """Запуск Telegram бота"""
    print("🚀 Запускаем Telegram бота...")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start),
                MessageHandler(filters.Text("📝 Записаться на консультацию"), handle_application_button)
            ],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
                PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_problem)],
                DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_datetime)],
                CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_application)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv_handler)
        
        print("✅ Telegram бот запущен и работает!")
        print("🤖 Бот готов принимать сообщения!")
        
        # Запускаем бота
        application.run_polling(
            drop_pending_updates=True,
            close_loop=False
        )
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

def run_flask():
    """Запуск Flask сервера"""
    print("🌐 Запускаем Flask сервер...")
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    print("🤖 Инициализация бота...")
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем бота в основном потоке
    run_bot()
