import json
import logging
import uuid
import datetime
import threading
import time
from typing import Any, Dict, List
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler, CommandHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN = "001.3014776720.0345725419:1011867925"
bot = Bot(token=TOKEN)

# pending_requests хранит запросы по ключу user_id, где значение — словарь с request_id как ключами.
# Структура: { user_id: { request_id: { "text": ..., "group": ..., "requester_id": ..., "expiry": ... } } }
pending_requests: Dict[str, Dict[str, Any]] = {}
# Голосования: { request_id: { responder_id: "approved"|"rejected" } }
approval_votes: Dict[str, Dict[str, str]] = {}
# Информация о группах: { chat_id: { "groupId": ..., "groupName": ..., "members": [...] } }
chat_members: Dict[str, Dict[str, Any]] = {}

def create_inline_keyboard(buttons_list: List[List[Dict[str, str]]]) -> str:
    return json.dumps(buttons_list)

def parse_expiry_time(input_text: str) -> datetime.datetime:
    """
    Разбирает ввод пользователя для определения времени окончания голосования.
    Допустимые форматы:
        • "N мин" — через N минут
        • "HH:MM" — сегодня в указанное время (если время уже прошло, то на следующий день)
        • "DD.MM HH:MM" — указанная дата и время (текущий год)
        • "DD.MM.YYYY HH:MM" — полная дата и время
    """
    now = datetime.datetime.now()
    try:
        if "мин" in input_text:
            minutes = int(input_text.split()[0])
            return now + datetime.timedelta(minutes=minutes)
        elif ":" in input_text and len(input_text.split()) == 1:
            hour, minute = map(int, input_text.split(":"))
            expiry_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return expiry_time if expiry_time > now else expiry_time + datetime.timedelta(days=1)
        elif len(input_text.split()) == 2:
            date_part, time_part = input_text.split()
            day, month = map(int, date_part.split("."))
            hour, minute = map(int, time_part.split(":"))
            year = now.year
            expiry_time = datetime.datetime(year, month, day, hour, minute)
            return expiry_time if expiry_time > now else expiry_time.replace(year=year + 1)
        elif len(input_text.split(".")) == 3:
            # Ожидаем формат: DD.MM.YYYY HH:MM
            parts = input_text.split()
            if len(parts) != 2:
                return None
            date_part, time_part = parts
            day, month, year = map(int, date_part.split("."))
            hour, minute = map(int, time_part.split(":"))
            return datetime.datetime(year, month, day, hour, minute)
    except Exception as e:
        logging.error(f"Ошибка парсинга времени: {e}")
    return None

def start_vote_timer(user_id: str, request_id: str, deadline: float, group_id: str) -> None:
    """
    Ждет до истечения срока голосования и вызывает finalize_vote.
    """
    sleep_duration = deadline - time.time()
    if sleep_duration > 0:
        time.sleep(sleep_duration)
    finalize_vote(user_id, request_id, group_id)

def finalize_vote(user_id: str, request_id: str, group_id: str) -> None:
    """
    Подводит итоги голосования для запроса с request_id.
    Отправляет итог создателю и уведомляет тех, кто не проголосовал.
    Затем удаляет запрос из pending_requests и approval_votes.
    """
    if user_id not in pending_requests or request_id not in pending_requests[user_id]:
        return
    request_data = pending_requests[user_id][request_id]
    votes = approval_votes.get(request_id, {})
    approved_count = sum(1 for v in votes.values() if v == "approved")
    rejected_count = sum(1 for v in votes.values() if v == "rejected")
    summary = f"Голосование завершено! Одобрено: {approved_count}, Отклонено: {rejected_count}"
    requester_id = request_data.get("requester_id", user_id)
    bot.send_text(chat_id=requester_id, text=summary)
    group_info = chat_members.get(group_id, {})
    members = group_info.get("members", [])
    for member in members:
        if member not in votes and member != requester_id:
            bot.send_text(chat_id=member, text="Голосование закончилось.")
    del pending_requests[user_id][request_id]
    if request_id in approval_votes:
            if user_id in pending_requests:
                if not pending_requests[user_id]:  # Если запросов больше нет, удаляем запись пользователя
                    del pending_requests[user_id]
            del approval_votes[request_id]

def show_main_menu(bot: Bot, chat_id: str, is_private_chat: bool) -> None:
    if is_private_chat:
        text = "Привет! У тебя появилась идея? Давай, покажем её"
        buttons = [
            [{"text": "Создать запрос на апрув", "callbackData": "create_approval_request"}],
            [{"text": "Посмотреть статус запросов", "callbackData": "to_requests_menu"}]
        ]
    else:
        text = "Привет, чат!"
        buttons = [[{"text": "Обновить участников чата", "callbackData": "update_members"}]]
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))

def show_requests_menu(bot: Bot, chat_id) -> None:
    text = "Статус запросов"
    buttons = [
        #[{"text": "Список твоих запросов", "callbackData": "show_your_requests"}],
        [{"text": "Список твоих запросов", "callbackData": "no_callback"}],
        #[{"text": "Твои голосования", "callbackData": "show_another's_requests"}],
        [{"text": "Твои голосования", "callbackData": "no_callback"}],
        [{"text": "Назад в главное меню", "callbackData": "to_main_menu"}],
    ]
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))

def show_available_groups(bot: Bot, user_id: str) -> None:
    available_groups = [group_info for group_info in chat_members.values() if user_id in group_info.get("members", [])]
    if not available_groups:
        bot.send_text(chat_id=user_id, text="Вы не состоите в группах с ботом.")
        return
    buttons = [
        [{"text": group["groupName"], "callbackData": f"choose_group_{group['groupId']}"}]
        for group in available_groups
    ]
    bot.send_text(chat_id=user_id, text="Выберите группу для отправки запроса:", inline_keyboard_markup=create_inline_keyboard(buttons))

def handle_buttons(bot: Bot, event: Any) -> None:
    callback_data = event.data.get("callbackData", "")
    chat_id = event.from_chat
    user_id = event.data.get("from", {}).get("userId", "")
    request_id = ""

    if callback_data == "update_members":
        update_members(bot, chat_id)
        return

    if callback_data == "create_approval_request":
        request_id = str(uuid.uuid4())
        if user_id not in pending_requests:
            pending_requests[user_id] = {}
        pending_requests[user_id][request_id] = {"text": "", "group": "", "requester_id": user_id, "expiry": None}
        bot.send_text(chat_id=user_id, text="Введите описание запроса на апрув:")
        return

    if callback_data == "to_requests_menu":
        show_requests_menu(bot, chat_id)
        return

    if callback_data == "to_main_menu":
        show_main_menu(bot, chat_id, True)  # Показать главное меню
        return

    if callback_data.startswith("choose_group_"):
        group_id = callback_data.replace("choose_group_", "")
        if user_id in pending_requests and len(pending_requests[user_id]) > 0:
            request_id = list(pending_requests[user_id].keys())[-1]
            pending_requests[user_id][request_id]["group"] = group_id
            bot.send_text(chat_id=user_id, text="Введите время окончания голосования в одном из следующих форматов:\n"
                "🔹 `HH:MM` – сегодня в указанное время\n"
                "🔹 `N мин` – через N минут\n"
                "🔹 `DD.MM HH:MM` – указанная дата и время\n"
                "🔹 `DD.MM.YYYY HH:MM` – полная дата и время")
        return

    if callback_data.startswith("approve_"):
        request_id = callback_data.split("_", 1)[1]
        if request_id in approval_votes and user_id in approval_votes[request_id]:
            bot.send_text(chat_id=event.from_chat, text="Вы уже проголосовали.")
            return
        approval_votes.setdefault(request_id, {})[user_id] = "approved"
        bot.send_text(chat_id=event.from_chat, text="Вы одобрили запрос.")
        found_request = False
        for requester, requests_dict in pending_requests.items():
            if request_id in requests_dict:
                requester_id = requests_dict[request_id].get("requester_id")
                request_text = requests_dict[request_id].get("text", "Нет текста запроса")
                bot.send_text(chat_id=requester_id, text=f"Пользователь {user_id} одобрил ваш запрос: {request_text}")
                found_request = True
                return
        if not found_request:
            logging.error(f"Запрос с request_id {request_id} не найден.")
        return

    if callback_data.startswith("reject_"):
        request_id = callback_data.split("_", 1)[1]
        if request_id in approval_votes and user_id in approval_votes[request_id]:
            bot.send_text(chat_id=event.from_chat, text="Вы уже проголосовали.")
            return
        approval_votes.setdefault(request_id, {})[user_id] = "rejected"
        bot.send_text(chat_id=event.from_chat, text="Вы отклонили запрос.")
        found_request = False
        for requester, requests_dict in pending_requests.items():
            if request_id in requests_dict:
                requester_id = requests_dict[request_id].get("requester_id")
                request_text = requests_dict[request_id].get("text", "Нет текста запроса")
                bot.send_text(chat_id=requester_id, text=f"Пользователь {user_id} отклонил ваш запрос: {request_text}")
                found_request = True
                return
        if not found_request:
            logging.error(f"Запрос с request_id {request_id} не найден.")
        return

    # !!! Убрать это после разработки
    if callback_data == "no_callback":
        return
    # !!!

    # Показать главное меню после завершения обработки кнопок
    show_main_menu(bot, chat_id, chat_id in chat_members)

def handle_message(bot: Bot, event: Any) -> None:
    user_id = event.data.get("from", {}).get("userId", "")
    chat_id = event.from_chat
    chat_type = event.data.get("chat", {}).get("type", "")
    is_private_chat = chat_type == "private"

    # Проверяем, что бот не находится в состоянии ожидания и может продолжить работу
    if user_id in pending_requests and len(pending_requests[user_id]) > 0:
        request_id = list(pending_requests[user_id].keys())[-1]
        if pending_requests[user_id][request_id]["text"] == "":
            pending_requests[user_id][request_id]["text"] = event.data.get("text", "")
            show_available_groups(bot, user_id)
        elif pending_requests[user_id][request_id]["expiry"] is None:
            expiry_time = parse_expiry_time(event.data.get("text", ""))
            if expiry_time:
                pending_requests[user_id][request_id]["expiry"] = expiry_time.strftime("%Y-%m-%d %H:%M")
                threading.Thread(target=start_vote_timer, args=(user_id, request_id, expiry_time.timestamp(), pending_requests[user_id][request_id]["group"])).start()
                send_approval_request(bot, user_id, pending_requests[user_id][request_id]["group"], request_id)
            else:
                bot.send_text(chat_id=user_id, text="Неверный формат времени. Попробуйте снова.")
    else:
        show_main_menu(bot, chat_id, is_private_chat)

def update_members(bot: Bot, chat_id: str) -> None:
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
    available_groups = [group_info for group_info in chat_members.values() if user_id in group_info.get("members", [])]
    if not available_groups:
        bot.send_text(chat_id=user_id, text="Вы не состоите в группах с ботом.")
        return
    buttons = [
        [{"text": group["groupName"], "callbackData": f"choose_group_{group['groupId']}"}]
        for group in available_groups
    ]
    bot.send_text(chat_id=user_id, text="Выберите группу для отправки запроса:", inline_keyboard_markup=create_inline_keyboard(buttons))

def send_approval_request(bot: Bot, user_id: str, group_id: str, request_id: str) -> None:
    request_data = pending_requests.get(user_id, {}).get(request_id, {})
    request_text = request_data.get("text", "")
    expiry_time = request_data.get("expiry", "")
    if not request_text:
        return
    group_info = chat_members.get(group_id, {})
    members = group_info.get("members", [])
    title = group_info.get("groupName", "...")
    response_buttons = create_inline_keyboard([
        [{"text": "✅ Одобрить", "callbackData": f"approve_{request_id}"}],
        [{"text": "❌ Отклонить", "callbackData": f"reject_{request_id}"}]
    ])
    for member in members:
        if member != user_id:
            bot.send_text(chat_id=member, 
                text=f"Запрос на апрув от {user_id} из группы '{title}':\n{request_text}\n⏳ Голосование до: {expiry_time}",
                inline_keyboard_markup=response_buttons)
    bot.send_text(chat_id=user_id, text="Запрос отправлен!")

    show_main_menu(bot, user_id, True)

# Регистрация обработчиков
bot.dispatcher.add_handler(MessageHandler(callback=handle_message))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback=handle_buttons))
bot.dispatcher.add_handler(CommandHandler(command="/update_members", callback=update_members))

logging.info("Бот запущен и ожидает сообщений...")
bot.start_polling()
bot.idle()
