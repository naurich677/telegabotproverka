import logging
import pdfplumber
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Токен бота, предоставленный вами
TOKEN = '7992492738:AAF1lD3pXjX6U4QDQY5Mox_MHC-tMoXWl8g'

# Глобальное множество для хранения ID пользователей (для последующей рассылки)
user_ids = set()

# Глобальный словарь для хранения данных пользователей (например, выбранный тариф)
user_data = {}

# ID администратора для рассылки (только он сможет запускать команду /broadcast)
admin_ids = [6376202109]

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def add_user_id(user_id):
    user_ids.add(user_id)

def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    first_name = update.effective_user.first_name
    # Сохраняем ID пользователя для последующих рассылок
    add_user_id(chat_id)
    
    # Отправляем фотографию по ссылке
    photo_url = 'https://i.ibb.co/5h8QG87h/IMG-0821.jpg'
    update.message.reply_photo(photo=photo_url)
    
    # Приветственное сообщение с текстом согласно сценарию
    welcome_text = (
        "Жанадан шығып жаткан отандық жана шетелдік кино, сериалдарды биринчи болуп көрініз🔥\n"
        "KoremizKino VIP каналға доступты осы жерден аласыз ⬇️\n"
        "Сатып алу:"
    )
    # Inline-кнопка "ДОСТУП АЛУ"
    keyboard = [[InlineKeyboardButton("ДОСТУП АЛУ", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    # Отправляем также обычную кнопку "Поддержка"
    reply_keyboard = [['Поддержка']]
    update.message.reply_text("Выберите опцию:",
                                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if data == 'start':
        # Выводим варианты тарифов
        keyboard = [
            [InlineKeyboardButton("3 ай доступ (1000тг)", callback_data='tariff_1000')],
            [InlineKeyboardButton("Шексіз доступ (1990тг)", callback_data='tariff_1990')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text("Төлем жасау үшін тарифті танданыз", reply_markup=reply_markup)
    elif data.startswith('tariff_'):
        tariff = data.split('_')[1]  # Получаем '1000' или '1990'
        user_data[chat_id] = {'tariff': tariff}
        if tariff == '1000':
            text = (
                "3 ай доступ алу үшін ушул реквезитке точна 1000тг салып чекті ботқа PDF форматта жіберініз !\n\n"
                "4400 4303 6182 4656"
            )
        elif tariff == '1990':
            text = (
                "Шексіз доступ алу үшін ушул реквезитке ровна 1990тг салып чекті ботқа PDF форматта жіберініз !\n\n"
                "4400 4303 6182 4656"
            )
        query.message.edit_text(text)
        # Если в течение 15 минут PDF не прислан – отправляем бонусное сообщение
        context.job_queue.run_once(timeout_callback, 15 * 60, context=chat_id)

def timeout_callback(context: CallbackContext):
    job = context.job
    chat_id = job.context
    context.bot.send_message(chat_id, "Бүгін төлем жасасаныз бонусқа 99курс беріледі !")

def document_handler(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id not in user_data or 'tariff' not in user_data[chat_id]:
        update.message.reply_text("Пожалуйста, сначала выберите тариф через кнопку ДОСТУП АЛУ.")
        return

    document = update.message.document
    if document.mime_type != 'application/pdf':
        update.message.reply_text("Пожалуйста, отправьте PDF файл.")
        return

    file = document.get_file()
    file_path = f"/tmp/{document.file_id}.pdf"
    file.download(custom_path=file_path)

    try:
        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text
    except Exception as e:
        update.message.reply_text("Ошибка при чтении PDF файла.")
        logger.error(e)
        return

    expected_sum = user_data[chat_id]['tariff']
    if expected_sum in full_text:
        access_link = "https://t.me/+U3i7xK98ODRmZDNi"
        update.message.reply_text(f"Оплата прошла успешно! Ваш доступ: {access_link}")
    else:
        update.message.reply_text(
            f"❌Қате чек сомасы {expected_sum}тг емес. Төлем ровна {expected_sum}тг болу қажет !\n"
            "Егер артық жиберген болсаныз, поддержкаға жазыныз!"
        )

def support_handler(update: Update, context: CallbackContext):
    update.message.reply_text("Поддержка: https://t.me/koremizkinopod")

def broadcast(update: Update, context: CallbackContext):
    # Только администратор может запускать рассылку
    if update.effective_user.id not in admin_ids:
        update.message.reply_text("Нет доступа!")
        return
    args = context.args
    if not args:
        update.message.reply_text("Пожалуйста, укажите текст рассылки после команды /broadcast")
        return
    message_text = ' '.join(args)
    for user_id in user_ids:
        try:
            context.bot.send_message(user_id, message_text)
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
    update.message.reply_text("Рассылка завершена!")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.document.pdf, document_handler))
    dp.add_handler(MessageHandler(Filters.regex('^(Поддержка)$'), support_handler))
    dp.add_handler(CommandHandler("broadcast", broadcast, pass_args=True))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
