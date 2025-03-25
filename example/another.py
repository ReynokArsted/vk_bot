import json
import logging
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler, CommandHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN = "001.3014776720.0345725419:1011867925"  # Укажите реальный токен
bot = Bot(token=TOKEN)
chat_members = {}  # Словарь для хранения участников чатов

def create_inline_keyboard(buttons_list):
    """Формирует JSON-разметку для inline-кнопок"""
    return json.dumps(buttons_list)

def show_main_menu(bot, chat_id, is_private_chat):
    """Отправляет главное меню пользователю"""
    # Кнопки для личного чата
    if is_private_chat:
        mes = "Привет! У тебя появилась идея? Давай, покажем её"
        buttons = [
            [{"text": "Создать предложение по задаче", "callbackData": "call_back_id_1"}],
            [{"text": "Посмотреть статус твоих предложений для задач", "callbackData": "call_back_id_2"}]
        ]
    # Кнопки для общего чата
    else:
        mes = "Привет, чат!"
        buttons = [
            [{"text": "Обновить участников чата", "callbackData": "update_members"}]
        ]
    
    bot.send_text(
        chat_id=chat_id,
        text=mes,
        inline_keyboard_markup=create_inline_keyboard(buttons)
    )

def handle_buttons(bot, event):
    """Обрабатывает нажатия кнопок"""
    callback_data = event.data.get("callbackData", "")
    chat_id = event.from_chat
    chat_type = event.data.get("chat", {}).get("type", "")  # Получаем тип чата

    is_private_chat = chat_type == "private"  # Проверяем, является ли чат личным

    if callback_data == "update_members":
        update_members(bot, chat_id)
        return
    
    responses = {
        "call_back_id_1": (
            "Запрос на апрув может состоять из текста, ссылок на внешние ресурсы "
            "и прикреплённых картинок. Ещё можно задать время, в течение которого "
            "будут ожидаться апрувы. После ты получишь напоминание от меня о запросе.\n\n"
            "Начнём с описания предложения. Давай, опишем его:",
            [[{"text": "Назад", "callbackData": "back_to_main_menu"}]]
        ),
        "call_back_id_2": (
            "Список предложений",
            [
                [{"text": "Назад", "callbackData": "back_to_main_menu"}],
                [{"text": "Предложение 1", "callbackData": ""}],
                [{"text": "Предложение 2", "callbackData": ""}],
                [{"text": "Предложение 3", "callbackData": ""}]
            ]
        ),
        "back_to_main_menu": (None, None)
    }

    if callback_data == "call_back_id_1" and not is_private_chat:
        bot.send_text(chat_id=chat_id, text="Вы можете создавать запросы на апрув только в личном чате с ботом.")
        return

    if callback_data in responses:
        text, buttons = responses[callback_data]
        if text:
            bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))
        else:
            show_main_menu(bot, chat_id, is_private_chat)
    else:
        logging.warning(f"Неизвестный callbackData: {callback_data}")

def update_members(bot, chat_id):
    """Получает и сохраняет список участников чата"""
    try:
        response = bot.get_chat_members(chat_id).json()
        members = response.get('members', [])
        chat_members[chat_id] = [member["userId"] for member in members]  # Извлекаем userId каждого участника
        bot.send_text(chat_id=chat_id, text=f"Список участников обновлён: {len(chat_members[chat_id])} человек.")
    except Exception as e:
        logging.error(f"Ошибка при получении участников чата: {e}")
        bot.send_text(chat_id=chat_id, text="Не удалось обновить список участников чата.")

def handle_message(bot, event):
    """Обрабатывает входящие сообщения и вызывает главное меню"""
    chat_type = event.data.get("chat", {}).get("type", "")  # Получаем тип чата  # Получаем данные события
    is_private_chat = chat_type == "private"  # Проверяем, является ли чат личным
    show_main_menu(bot, event.from_chat, is_private_chat)

# Регистрация обработчиков
bot.dispatcher.add_handler(MessageHandler(callback=handle_message))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback=handle_buttons))
bot.dispatcher.add_handler(CommandHandler(command="/update_members", callback=update_members))

logging.info("Бот запущен и ожидает сообщений...")
bot.start_polling()
bot.idle()
