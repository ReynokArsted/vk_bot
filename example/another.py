import json
import logging
from typing import Any, Dict, List
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler, CommandHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN = "001.3014776720.0345725419:1011867925"
bot = Bot(token=TOKEN)

# Глобальные словари для хранения данных
chat_members: Dict[str, Dict[str, Any]] = {}      # Информация о группах: {chat_id: {"groupId": ..., "groupName": ..., "members": [...]}}
pending_requests: Dict[str, Dict[str, str]] = {}    # Запросы на апрув: {user_id: {"text": ..., "group": ...}}
approval_votes: Dict[str, Dict[str, str]] = {}      # Голосования: {requester_id: {responder_id: "approved"|"rejected"}}

def create_inline_keyboard(buttons_list: List[List[Dict[str, str]]]) -> str:
    """Возвращает JSON-строку для inline-кнопок."""
    return json.dumps(buttons_list)

def show_main_menu(bot: Bot, chat_id: str, is_private_chat: bool) -> None:
    """
    Отправляет главное меню пользователю.
    В личном чате доступны кнопки для создания запроса и просмотра статуса,
    в групповом – только кнопка обновления списка участников.
    """
    if is_private_chat:
        text = "Привет! У тебя появилась идея? Давай, покажем её"
        buttons = [
            [{"text": "Создать запрос на апрув", "callbackData": "create_approval_request"}],
            [{"text": "Посмотреть статус запросов", "callbackData": "view_requests"}]
        ]
    else:
        text = "Привет, чат!"
        buttons = [[{"text": "Обновить участников чата", "callbackData": "update_members"}]]
    
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))

def handle_buttons(bot: Bot, event: Any) -> None:
    """
    Обрабатывает нажатия кнопок.
    Помимо стандартных действий, обрабатывает кнопки одобрения и отклонения запроса,
    и проверяет, если пользователь уже голосовал.
    """
    callback_data = event.data.get("callbackData", "")
    chat_id = event.from_chat
    user_id = event.data.get("from", {}).get("userId", "")
    
    if callback_data == "update_members":
        update_members(bot, chat_id)
        return
    
    if callback_data == "create_approval_request":
        pending_requests[user_id] = {"text": "", "group": ""}
        bot.send_text(chat_id=user_id, text="Введите описание запроса на апрув:")
        return
    
    if callback_data.startswith("choose_group_"):
        group_id = callback_data.replace("choose_group_", "")
        if user_id in pending_requests:
            pending_requests[user_id]["group"] = group_id
            send_approval_request(bot, user_id, group_id)
        return
    
    # Обработка кнопок одобрения и отклонения
    if callback_data.startswith("approve_"):
        # Формат callbackData: "approve_<requester_id>"
        requester_id = callback_data.split("_", 1)[1]
        # Проверяем, если пользователь уже голосовал за этот запрос
        if requester_id in approval_votes and user_id in approval_votes[requester_id]:
            bot.send_text(chat_id=event.from_chat, text="Вы уже проголосовали.")
            return
        # Записываем голос за запрос
        approval_votes.setdefault(requester_id, {})[user_id] = "approved"
        bot.send_text(chat_id=event.from_chat, text="Вы одобрили запрос.")
        bot.send_text(chat_id=requester_id, text=f"Пользователь {user_id} одобрил ваш запрос.")
        return
    
    if callback_data.startswith("reject_"):
        # Формат callbackData: "reject_<requester_id>"
        requester_id = callback_data.split("_", 1)[1]
        if requester_id in approval_votes and user_id in approval_votes[requester_id]:
            bot.send_text(chat_id=event.from_chat, text="Вы уже проголосовали.")
            return
        approval_votes.setdefault(requester_id, {})[user_id] = "rejected"
        bot.send_text(chat_id=event.from_chat, text="Вы отклонили запрос.")
        bot.send_text(chat_id=requester_id, text=f"Пользователь {user_id} отклонил ваш запрос.")
        return

    show_main_menu(bot, chat_id, chat_id in chat_members)

def handle_message(bot: Bot, event: Any) -> None:
    """
    Обрабатывает входящие текстовые сообщения.
    Если пользователь находится в процессе создания запроса и еще не ввёл текст – сохраняет его и предлагает выбрать группу.
    Иначе – выводит главное меню.
    """
    user_id = event.data.get("from", {}).get("userId", "")
    chat_id = event.from_chat
    chat_type = event.data.get("chat", {}).get("type", "")
    is_private_chat = chat_type == "private"
    
    if user_id in pending_requests and not pending_requests[user_id]["text"]:
        pending_requests[user_id]["text"] = event.data.get("text", "")
        show_available_groups(bot, user_id)
    else:
        show_main_menu(bot, chat_id, is_private_chat)

def update_members(bot: Bot, chat_id: str) -> None:
    """
    Обновляет список участников чата.
    Получает данные о членах и информацию о чате для формирования названия группы.
    """
    try:
        response = bot.get_chat_members(chat_id).json()
        logging.info(f"Ответ от API (get_chat_members): {response}")
        members = response.get('members', [])
        member_ids = [member.get("userId", "Неизвестно") for member in members]
        
        chat_info = bot.get_chat_info(chat_id).json()
        group_name = chat_info.get("title", "Неизвестно")
        
        chat_members[chat_id] = {
            "groupId": chat_id,
            "groupName": group_name,
            "members": member_ids
        }
        logging.info(f"Обновлённый список участников для {chat_id}: {chat_members[chat_id]['members']}")
        bot.send_text(chat_id=chat_id, text=f"Список участников обновлён: {len(member_ids)} человек.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении списка участников: {e}")
        bot.send_text(chat_id=chat_id, text="Ошибка при обновлении списка участников.")

def show_available_groups(bot: Bot, user_id: str) -> None:
    """
    Отображает список групп, в которых состоит пользователь и где находится бот.
    Кнопки формируются с использованием groupName для отображения и groupId для callbackData.
    """
    available_groups = [group_info for group_info in chat_members.values() if user_id in group_info["members"]]
    if not available_groups:
        bot.send_text(chat_id=user_id, text="Вы не состоите в группах с ботом.")
        return
    buttons = [
        [{"text": group["groupName"], "callbackData": f"choose_group_{group['groupId']}"}]
        for group in available_groups
    ]
    bot.send_text(chat_id=user_id, text="Выберите группу для отправки запроса:", inline_keyboard_markup=create_inline_keyboard(buttons))

def send_approval_request(bot: Bot, user_id: str, group_id: str) -> None:
    """
    Отправляет запрос на апрув всем участникам выбранной группы, кроме создателя запроса.
    В сообщении добавляются кнопки для одобрения и отклонения запроса.
    """
    request_text = pending_requests.get(user_id, {}).get("text", "")
    if not request_text:
        return
    
    group_info = chat_members.get(group_id, {})
    members = group_info.get("members", [])
    title = group_info.get("groupName", "...")
    
    # Формируем inline-клавиатуру для ответа на запрос:
    response_buttons = create_inline_keyboard([
        [{"text": "✅ Одобрить", "callbackData": f"approve_{user_id}"}],
        [{"text": "❌ Отклонить", "callbackData": f"reject_{user_id}"}]
    ])
    
    for member in members:
        if member != user_id:
            bot.send_text(chat_id=member, 
                text=f"Запрос на апрув от {user_id} из группы '{title}':\n{request_text}",
                inline_keyboard_markup=response_buttons)
    
    bot.send_text(chat_id=user_id, text="Запрос отправлен!")
    del pending_requests[user_id]

# Регистрация обработчиков
bot.dispatcher.add_handler(MessageHandler(callback=handle_message))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback=handle_buttons))
bot.dispatcher.add_handler(CommandHandler(command="/update_members", callback=update_members))

logging.info("Бот запущен и ожидает сообщений...")
bot.start_polling()
bot.idle()
