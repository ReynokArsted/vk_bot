import json
import logging
import uuid  # Добавим для генерации уникальных ID
from typing import Any, Dict, List
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler, CommandHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN = "001.3014776720.0345725419:1011867925"
bot = Bot(token=TOKEN)

# Глобальные словари для хранения данных
chat_members: Dict[str, Dict[str, Any]] = {}      # Информация о группах: {chat_id: {"groupId": ..., "groupName": ..., "members": [...]}}
pending_requests: Dict[str, Dict[str, str]] = {}    # Запросы на апрув: {request_id: {"user_id": ..., "text": ..., "group": ...}}
approval_votes: Dict[str, Dict[str, str]] = {}      # Голосования: {request_id: {responder_id: "approved"|"rejected"}}

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
    request_id = ""
    
    if callback_data == "update_members":
        update_members(bot, chat_id)
        return

    if callback_data == "create_approval_request":
        # Генерация уникального ID для запроса
        request_id = str(uuid.uuid4())  

        # Сохраняем новый запрос в pending_requests
        if user_id not in pending_requests:
            pending_requests[user_id] = {}

        # Сохраняем новый запрос с уникальным request_id для данного пользователя
        pending_requests[user_id][request_id] = {
            "text": "", 
            "group": "", 
            "requester_id": user_id
        }

        # Спрашиваем описание запроса
        bot.send_text(chat_id=user_id, text="Введите описание запроса на апрув:")
        return
    
    #if callback_data.startswith("choose_group_"):
    #    group_id = callback_data.replace("choose_group_", "")  
    #    if user_id in pending_requests:
    #        request_id = str(uuid.uuid4())  # Генерация уникального ID для запроса
    #        pending_requests[user_id]["request_id"] = request_id
    #        pending_requests[user_id]["group"] = group_id
    #        pending_requests[user_id]["requester_id"] = user_id  # Сохраняем создателя запроса
    #        send_approval_request(bot, user_id, group_id, request_id)
    #    return

    if callback_data.startswith("choose_group_"):
        group_id = callback_data.replace("choose_group_", "")
    
        # Находим последний созданный запрос для пользователя
        if user_id in pending_requests and len(pending_requests[user_id]) > 0:
            # Получаем последний request_id для данного пользователя
            request_id = list(pending_requests[user_id].keys())[-1]
        
            # Обновляем группу для этого запроса
            pending_requests[user_id][request_id]["group"] = group_id
            pending_requests[user_id][request_id]["requester_id"] = user_id
        
            # Отправляем запрос на апрув
            send_approval_request(bot, user_id, group_id, request_id)
        return

    
    # Обработка кнопок одобрения и отклонения
    # В обработке кнопок approve и reject
    if callback_data.startswith("approve_"):
        request_id = callback_data.split("_", 1)[1]

        # Проверяем, проголосовал ли пользователь уже
        if request_id in approval_votes and user_id in approval_votes[request_id]:
            bot.send_text(chat_id=event.from_chat, text="Вы уже проголосовали.")
            return

        # Записываем голос
        approval_votes.setdefault(request_id, {})[user_id] = "approved"
        bot.send_text(chat_id=event.from_chat, text="Вы одобрили запрос.")

        # Отправляем сообщение создателю запроса
        requester_id = None
        for requester, requests in pending_requests.items():
            if request_id in requests:
                requester_id = requests[request_id].get("requester_id")
                # Завершаем функцию, если нашли нужный запрос
                request_text = requests[request_id].get("text", "Нет текста запроса")
                bot.send_text(chat_id=requester_id, text=f"Пользователь {user_id} одобрил ваш запрос: {request_text}")
                return  # Завершаем выполнение функции сразу

        # Если не нашли создателя запроса
        logging.error(f"Не удалось найти создателя запроса для request_id {request_id}")
        return

    if callback_data.startswith("reject_"):
        request_id = callback_data.split("_", 1)[1]

        # Проверяем, проголосовал ли пользователь уже
        if request_id in approval_votes and user_id in approval_votes[request_id]:
            bot.send_text(chat_id=event.from_chat, text="Вы уже проголосовали.")
            return

        # Записываем голос
        approval_votes.setdefault(request_id, {})[user_id] = "rejected"
        bot.send_text(chat_id=event.from_chat, text="Вы отклонили запрос.")

        # Отправляем сообщение создателю запроса
        requester_id = None
        for requester, requests in pending_requests.items():
            if request_id in requests:
                requester_id = requests[request_id].get("requester_id")
                # Завершаем функцию, если нашли нужный запрос
                request_text = requests[request_id].get("text", "Нет текста запроса")
                bot.send_text(chat_id=requester_id, text=f"Пользователь {user_id} отклонил ваш запрос: {request_text}")
                return  # Завершаем выполнение функции сразу

        # Если не нашли создателя запроса
        logging.error(f"Не удалось найти создателя запроса для request_id {request_id}")
        return

    show_main_menu(bot, chat_id, chat_id in chat_members)


def handle_message(bot: Bot, event: Any) -> None:
    """Обрабатывает входящие текстовые сообщения."""
    user_id = event.data.get("from", {}).get("userId", "")
    chat_id = event.from_chat
    chat_type = event.data.get("chat", {}).get("type", "")
    is_private_chat = chat_type == "private"
    
    # Проверяем, если пользователь в процессе создания запроса
    if user_id in pending_requests and len(pending_requests[user_id]) > 0:
        # Если у пользователя несколько запросов, берём последний созданный запрос
        request_id = list(pending_requests[user_id].keys())[-1]

        # Сохраняем текст запроса
        pending_requests[user_id][request_id]["text"] = event.data.get("text", "")
        
        # После этого предлагаем выбрать группу
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

def send_approval_request(bot: Bot, user_id: str, group_id: str, request_id: str) -> None:
    """
    Отправляет запрос на апрув всем участникам выбранной группы, кроме создателя запроса.
    В сообщении добавляются кнопки для одобрения и отклонения запроса.
    """
    print(pending_requests)
    
    # Получаем данные запроса по request_id
    request_data = pending_requests.get(user_id, {}).get(request_id, {})
    request_text = request_data.get("text", "")
    
    if not request_text:
        return
    
    group_info = chat_members.get(group_id, {})
    members = group_info.get("members", [])
    title = group_info.get("groupName", "...")
    
    # Сохраняем ID создателя запроса, если еще не сохранён
    if "requester_id" not in request_data:
        pending_requests[request_id]["requester_id"] = user_id
    
    # Формируем inline-клавиатуру для ответа на запрос
    response_buttons = create_inline_keyboard([
        [{"text": "✅ Одобрить", "callbackData": f"approve_{request_id}"}],
        [{"text": "❌ Отклонить", "callbackData": f"reject_{request_id}"}]
    ])
    
    # Отправляем запрос всем участникам, кроме создателя
    for member in members:
        if member != user_id:
            bot.send_text(chat_id=member, 
                text=f"Запрос на апрув от {user_id} из группы '{title}':\n{request_text}",
                inline_keyboard_markup=response_buttons)
    
    # Сообщаем создателю запроса, что запрос отправлен
    bot.send_text(chat_id=user_id, text="Запрос отправлен!")
    # Если нужно удалить запрос, можно раскомментировать следующую


# Регистрация обработчиков
bot.dispatcher.add_handler(MessageHandler(callback=handle_message))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback=handle_buttons))
bot.dispatcher.add_handler(CommandHandler(command="/update_members", callback=update_members))

logging.info("Бот запущен и ожидает сообщений...")
bot.start_polling()
bot.idle()
