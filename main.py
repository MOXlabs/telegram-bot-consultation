import os
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from flask import Flask
import threading

# Создаем Flask app для веб-сервера
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот для консультаций работает на Render! " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.route('/health')
def health():
    return "OK", 200

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
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8287276471:AAEfJuB-8GVERNkrnW4thGdU4B6JpnN4rmM')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '744451342')

WELCOME_PHOTO_URL = "https://i.ibb.co/yFdZ673f/Advocate.jpg"

def start(update: Update, context: CallbackContext):
    context.user_data['first_click'] = True

    try:
        update.message.reply_photo(
            photo=WELCOME_PHOTO_URL,
            caption="👋 Привет, я Арина - бот адвоката Алексея Мельникова. Я помогу Вам записаться на консультацию"
        )
    except Exception as e:
        update.message.reply_text(
            "👋 Привет, я Арина - бот адвоката Алексея Мельникова. Я помогу Вам записаться на консультацию"
        )

    keyboard = [[KeyboardButton("📝 Записаться на консультацию")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    update.message.reply_text(
        "Нажмите кнопку ниже чтобы начать заполнение заявки:",
        reply_markup=reply_markup)

def handle_application_button(update: Update, context: CallbackContext) -> int:
    is_first_click = context.user_data.get('first_click', True)

    if is_first_click:
        context.user_data['first_click'] = False
        update.message.reply_text(
            "Отлично! Давайте заполним заявку на консультацию.\n\n📝 Как к вам обращаться? (ФИО или имя)",
            reply_markup=ReplyKeyboardRemove())
    else:
        try:
            update.message.reply_photo(
                photo=WELCOME_PHOTO_URL,
                caption="👋 Снова здравствуйте! Заполним новую заявку на консультацию")
        except Exception:
            update.message.reply_text("👋 Снова здравствуйте! Заполним новую заявку на консультацию")

        update.message.reply_text(
            "📝 Как к вам обращаться? (ФИО или имя)",
            reply_markup=ReplyKeyboardRemove())

    return NAME

def get_name(update: Update, context: CallbackContext) -> int:
    context.user_data['name'] = update.message.text
    update.message.reply_text("📞 Укажите ваш номер телефона или другой способ связи:")
    return CONTACT

def get_contact(update: Update, context: CallbackContext) -> int:
    context.user_data['contact'] = update.message.text
    update.message.reply_text("❓ Кратко опишите суть проблемы:")
    return PROBLEM

def get_problem(update: Update, context: CallbackContext) -> int:
    context.user_data['problem'] = update.message.text
    update.message.reply_text("📅 Укажите желаемые дату и время для консультации:")
    return DATETIME

def get_datetime(update: Update, context: CallbackContext) -> int:
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

    update.message.reply_text(summary, reply_markup=reply_markup)
    return CONFIRM

def confirm_application(update: Update, context: CallbackContext) -> int:
    user_choice = update.message.text

    if user_choice == '✅ Да, отправить':
        send_application_to_admin(update, context)
        context.user_data['first_click'] = False

        keyboard = [[KeyboardButton("📝 Записаться на консультацию")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        update.message.reply_text(
            "✅ Спасибо! Ваша заявка отправлена. Мы свяжемся с вами в ближайшее время!\n\n",
            reply_markup=reply_markup)

        for key in ['name', 'contact', 'problem', 'datetime']:
            if key in context.user_data:
                del context.user_data[key]

        return ConversationHandler.END
    else:
        update.message.reply_text("🔄 Давайте заполним заявку заново.", reply_markup=ReplyKeyboardRemove())
        update.message.reply_text("📝 Как к вам обращаться? (ФИО или имя)")
        return NAME

def send_application_to_admin(update: Update, context: CallbackContext):
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
        context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=application_text)
        logger.info("Заявка отправлена администратору")
    except Exception as e:
        logger.error(f"Ошибка отправки заявки: {e}")

def cancel(update: Update, context: CallbackContext) -> int:
    context.user_data['first_click'] = False
    keyboard = [[KeyboardButton("📝 Записаться на консультацию")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    update.message.reply_text(
        '❌ Заявка отменена. Если захотите записаться, нажмите кнопку:',
        reply_markup=reply_markup)

    for key in ['name', 'contact', 'problem', 'datetime']:
        if key in context.user_data:
            del context.user_data[key]

    return ConversationHandler.END

def run_bot():
    """Запуск Telegram бота"""
    print("🚀 Запускаем Telegram бота на Render...")
    
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start),
                MessageHandler(Filters.text("📝 Записаться на консультацию"), handle_application_button)
            ],
            states={
                NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
                CONTACT: [MessageHandler(Filters.text & ~Filters.command, get_contact)],
                PROBLEM: [MessageHandler(Filters.text & ~Filters.command, get_problem)],
                DATETIME: [MessageHandler(Filters.text & ~Filters.command, get_datetime)],
                CONFIRM: [MessageHandler(Filters.text & ~Filters.command, confirm_application)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        updater.dispatcher.add_handler(CommandHandler("start", start))
        updater.dispatcher.add_handler(conv_handler)
        
        print("✅ Telegram бот запущен и работает на Render!")
        
        # Запускаем бота
        updater.start_polling(drop_pending_updates=True)
        updater.idle()
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🤖 Инициализация бота на Render...")
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
