import json
import logging
import uuid
import datetime
import threading
import time
import urllib.parse
from typing import Any, Dict, List
from bot.bot import Bot
from bot.handler import MessageHandler, BotButtonCommandHandler, CommandHandler, NewChatMembersHandler, LeftChatMembersHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN = "001.3014776720.0345725419:1011867925"
bot = Bot(token=TOKEN)

pending_requests: Dict[str, Dict[str, Any]] = {}
approval_votes: Dict[str, Dict[str, str]] = {}
chat_members: Dict[str, Dict[str, Any]] = {}
current_request: Dict[str, str] = {}
request_images: Dict[str, str] = {}  # Новый словарь для хранения image file_id по request_id

# Функции для кодировки названия групп и збежания ошибок в формата callback_data
def encode_for_callback(group_id: str, group_name: str) -> str:
    encoded_name = urllib.parse.quote(group_name)
    return f"choose_group_{group_id}|{encoded_name}"

def decode_from_callback(callback_data: str) -> tuple[str, str]:
    raw = callback_data.replace("choose_group_", "")
    if "|" in raw:
        group_id, encoded_name = raw.split("|", 1)
        group_name = urllib.parse.unquote(encoded_name)
    else:
        group_id = raw
        group_name = ""
    return group_id, group_name

def create_inline_keyboard(buttons_list: List[List[Dict[str, str]]]) -> str:
    return json.dumps(buttons_list)

def parse_expiry_time(input_text: str) -> datetime.datetime:
    """
    Разбирает ввод пользователя для определения времени окончания голосования.
    Допустимые форматы:
    • "N мин" — через N минут;
    • "HH:MM" — сегодня в указанное время (если время уже прошло, то следующий день);
    • "DD.MM HH:MM" — указанная дата и время (текущий год);
    • "DD.MM.YYYY HH:MM" — полная дата и время.
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
    sleep_duration = deadline - time.time()
    if sleep_duration > 0:
        time.sleep(sleep_duration)
    finalize_vote(user_id, request_id, group_id)

def finalize_vote(user_id: str, request_id: str, group_id: str) -> None:
    print(f"[DEBUG] finalize_vote was called!!!")
    if user_id not in pending_requests or request_id not in pending_requests[user_id]:
        return

    request_data = pending_requests[user_id][request_id]
    # Проверяем, был ли уже завершён запрос
    if request_data.get("vote_finalized", False):
        return  # Если уже завершён, не выполняем дальнейшую логику

    # Отметим, что голосование завершено
    request_data["vote_finalized"] = True

    votes = approval_votes.get(request_id, {})
    approved_users = [uid for uid, v in votes.items() if v == "approved" or v == "принят"]
    rejected_users = [uid for uid, v in votes.items() if v == "rejected" or v == "отклонён"]

    approved_count = sum(1 for v in votes.values() if v in ("approved", "принят"))
    rejected_count = sum(1 for v in votes.values() if v in ("rejected", "отклонён"))

    request_name = request_data.get("name", "Без названия")
    request_group = request_data.get("group_name", "Без названия")
    requester_id = request_data.get("requester_id", user_id)

    # Получаем инфу о группе
    group_info = chat_members.get(group_id, {})
    raw_members = group_info.get("members", [])

    # Словарь user_id -> display_name
    member_names = {
        m['userId']: m.get('name', m['userId']) for m in raw_members if isinstance(m, dict)
    }

    # Функция для отображения имени
    def get_display_name(uid: str) -> str:
        return member_names.get(uid, uid)

    # Списки имён
    approved_names = ", ".join(get_display_name(uid) for uid in approved_users) or "никто"
    rejected_names = ", ".join(get_display_name(uid) for uid in rejected_users) or "никто"

    non_voters = [
        uid for uid in member_names.keys()
        if uid not in votes and uid != requester_id
    ]
    non_voter_names = ", ".join(get_display_name(uid) for uid in non_voters) or "никто"


    # Результат голосования
    if approved_count > rejected_count:
        result_text = "Итог - ✅ Запрос одобрен!"
    elif rejected_count > approved_count:
        result_text = "Итог - ❌ Запрос отклонён!"
    else:
        result_text = "Итог - 🤷 Голоса разделились и решение не принято"

    # Финальное сообщение
    summary = (
        f"Голосование по запросу \"{request_name}\" в группе \"{request_group}\" завершено!\n\n"
        f"✅ За ({approved_count}): {approved_names}\n"
        f"❌ Против ({rejected_count}): {rejected_names}\n"
        f"❔ Не голосовали: {non_voter_names}\n\n"
        f"{result_text}"
    )

    #bot.send_text(chat_id=requester_id, text=summary)

    # Проверка наличия изображения
    image_file_id = request_data.get("image")
    
    print(f"[DEBUG] raw_members: {raw_members}")
    # Отправка сообщения с картинкой, если она есть
    if image_file_id != None:
        for member in raw_members:
            bot.send_file(chat_id=member, file_id=image_file_id, caption=summary)
    else:
        # Если изображения нет, отправляем только текст
        for member in raw_members:
            bot.send_text(chat_id=member, text=summary)    

    # Очистка
    del pending_requests[user_id][request_id]
    if request_id in approval_votes:
        del approval_votes[request_id]
    if not pending_requests[user_id]:
        del pending_requests[user_id]

def send_approval_request(bot: Bot, user_id: str, group_id: str, request_id: str) -> None:
    if group_id not in chat_members:
        logging.error(f"Группа {group_id} не найдена в chat_members")
        return

    members = chat_members[group_id]["members"]
    request_data = pending_requests[user_id][request_id]
    name = request_data.get("name", "Без названия")
    description = request_data.get("description", "")
    expiry = request_data.get("expiry", "не указано")
    group_name = request_data.get("group_name", "Без названия")
    image_id = request_data.get("image")

    text = f"📢 Новый запрос на апрув!\n\n" \
            f"🔹 *{name}*\n" \
            f"📝 {description}\n\n" \
            f"👤 Отправитель: {user_id}\n" \
            f"👥 Группа: {group_name}\n" \
            f"⏳ До: {expiry}"

    buttons = [
        [{"text": "✅ Одобрить", "callbackData": f"approve_{request_id}"}],
        [{"text": "❌ Отклонить", "callbackData": f"reject_{request_id}"}]
    ]

    for member_id in members:
        if member_id == user_id:
            continue
            
        if (image_id != None and image_id != "empty"):
            bot.send_file(
                chat_id=member_id,
                file_id=image_id,
                caption=text,
                inline_keyboard_markup=create_inline_keyboard(buttons)
            )
        else:
            bot.send_text(
                chat_id=member_id,
                text=text,
                inline_keyboard_markup=create_inline_keyboard(buttons)
            )

    bot.send_text(chat_id=user_id, text="✅ Запрос отправлен!")
    show_main_menu(bot, user_id, True)

def show_main_menu(bot: Bot, chat_id: str, is_private_chat: bool) -> None:
    if is_private_chat:
        text = "Привет! Создадим запрос на апрув?"
        buttons = [
            [{"text": "Создать запрос на апрув", "callbackData": "create_approval_request"}],
            [{"text": "Посмотреть статус запросов", "callbackData": "to_requests_menu"}]
        ]
    else:
        text = "Привет, чат!"
        buttons = [[{"text": "Обновить участников чата", "callbackData": "update_members"}]]
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))

def show_requests_menu(bot: Bot, chat_id: str) -> None:
    text = "Статус запросов"
    buttons = [
        [{"text": "Список ваших запросов", "callbackData": "show_your_requests"}],
        [{"text": "Ваши голосования", "callbackData": "show_your_votes"}],
        [{"text": "Назад в главное меню", "callbackData": "to_main_menu"}],
    ]
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))

def show_request_groups(bot: Bot, user_id: str, chat_id: str) -> None:
    user_requests = pending_requests.get(user_id, {})
    groups = {}
    for req_id, data in user_requests.items():
        grp = data.get("group", "")
        if grp:
            groups[grp] = chat_members.get(grp, {}).get("groupName", grp)
    if not groups:
        bot.send_text(chat_id=chat_id, text = "У тебя пока нет активных запросов")
        return
    buttons = [
        [{"text": group_name, "callbackData": f"view_requests_group_{group_id}"}]
        for group_id, group_name in groups.items()
    ]
    buttons.append([{"text": "Назад", "callbackData": "to_requests_menu"}])
    bot.send_text(chat_id=chat_id, text = "Выбери группу, для которой хочешь посмотреть запросы", inline_keyboard_markup=create_inline_keyboard(buttons))

def show_requests_for_group(bot: Bot, user_id: str, group_id: str, chat_id: str) -> None:
    user_requests = pending_requests.get(user_id, {})
    buttons = []
    for req_id, data in user_requests.items():
        if data.get("group", "") == group_id:
            request_name = data.get("name", "Без названия")
            buttons.append([{"text": request_name, "callbackData": ""}])
    group_name = chat_members.get(group_id, {}).get("groupName", group_id)
    if not buttons:
        bot.send_text(chat_id=chat_id, text=f"В группе \"{group_name}\" нет активных запросов")
        return
    buttons.append([{"text": "Назад", "callbackData": "to_requests_menu"}])
    bot.send_text(chat_id=chat_id,
                text=f'Запросы в группе "{group_name}":',
                inline_keyboard_markup=create_inline_keyboard(buttons))

def show_your_votes(bot: Bot, user_id: str, chat_id: str) -> None:
    votes_info = []
    for req_id, responses in approval_votes.items():
        if user_id in responses:
            status = responses[user_id]
            found_request = False
            for requester, req_dict in pending_requests.items():
                if req_id in req_dict:
                    req_data = req_dict[req_id]
                    request_name = req_data.get("name", "Без названия")
                    requester_id = req_data.get("requester_id", "Неизвестно")
                    group_id = req_data.get("group", "")
                    group_name = chat_members.get(group_id, {}).get("groupName", group_id)
                    votes_info.append(f'Запрос "{request_name}" от {requester_id} (группа: {group_name}) — {status}')
                    found_request = True
                    break
            if not found_request:
                votes_info.append(f"Запрос {req_id} — информация не найдена")
    if not votes_info:
        bot.send_text(chat_id=chat_id, text="У тебя пока нет голосований")
    else:
        bot.send_text(chat_id=chat_id, text="\n\n".join(votes_info))

def show_available_groups(bot: Bot, user_id: str) -> None:
    available_groups = [
        group_info for group_info in chat_members.values() 
        if user_id in group_info.get("members", [])
    ]

    if not available_groups:
        bot.send_text(
            chat_id=user_id, 
            text = "Этого бота нет в группах, в которых ты состоишь"
        )
        return

    buttons = [
        [{"text": group["groupName"], 
        "callbackData": encode_for_callback(group["groupId"], group["groupName"])}]
        for group in available_groups
    ]

    bot.send_text(
        chat_id=user_id, 
        text = "Выбирай группу для отправки запроса", 
        inline_keyboard_markup=create_inline_keyboard(buttons)
    )

def show_preview_request(bot: Bot, user_id: str):
    request_id = current_request.get(user_id)
    if not request_id:
        return

    req = pending_requests[user_id][request_id]
    text = f"**Предпросмотр запроса**\n\n" \
            f"📢 Новый запрос на апрув!\n\n" \
            f"📌 Название: {req['name']}\n" \
            f"📝 Описание: {req['description']}\n\n" \

    keyboard = create_inline_keyboard([
        [{"text": "✅ Всё верно", "callbackData": "preview_ok"}],
        [{"text": "✏️ Изменить", "callbackData": "preview_edit"}]
    ])

    if req["image"]:  # только если реально есть картинка
        bot.send_file(
            chat_id=user_id, 
            file_id=req["image"], 
            caption=text, 
            inline_keyboard_markup=keyboard
        )
    else:
        bot.send_text(
            chat_id=user_id, 
            text=text, 
            inline_keyboard_markup=keyboard
        )


def handle_buttons(bot: Bot, event: Any) -> None:
    callback_data = event.data.get("callbackData", "")
    chat_id = event.from_chat
    user_id = event.data.get("from", {}).get("userId", "")
    request_id = ""

    if callback_data == "no_image" and user_id in pending_requests:
        request_id = list(pending_requests[user_id].keys())[-1]
        pending_requests[user_id][request_id]["image"] = None
        pending_requests[user_id][request_id]["stage"] = "group"
        show_preview_request(bot, user_id)
        return

    
    elif callback_data == "preview_ok":
        show_available_groups(bot, user_id)
        return

    elif callback_data == "preview_edit":
        request_id = current_request.get(user_id)
        if request_id:
            req = pending_requests[user_id][request_id]
            req.update({
                "name": "",
                "description": "",
                "image": None,
                "group": "",
                "group_name": "",
                "expiry": None,
                "stage": "name",
                "vote_finalized": False  # Флаг, указывающий, завершено ли голосование
            })
            bot.send_text(chat_id=user_id, text="Окей, начнём редактирование. Введи название запроса:")
        return

    if callback_data == "create_approval_request":
        # Генерация нового запроса (если пользователь уже создавал запрос, он сбрасывается)
        request_id = str(uuid.uuid4())
        current_request[user_id] = request_id  # сохраняем id текущего запроса
        pending_requests.setdefault(user_id, {})[request_id] = {
            "name": "",
            "description": "",
            "group": "",
            "group_name": "",
            "requester_id": user_id,
            "expiry": None,
            "image": None,
            "stage": "name",
            "vote_finalied": False
        }
        bot.send_text(chat_id=user_id, text = "Как назовём запрос на апрув?")
        return

    if callback_data in {"to_main_menu", "update_members", "to_requests_menu", "show_your_requests", "show_your_votes"}:
        # Удаляем только текущий незавершенный запрос, если такой есть
        if user_id in current_request:
            current_id = current_request[user_id]
            if user_id in pending_requests and current_id in pending_requests[user_id]:
                req_data = pending_requests[user_id][current_id]
                if not req_data.get("group") or not req_data.get("expiry"):
                    del pending_requests[user_id][current_id]
                    if not pending_requests[user_id]:
                        del pending_requests[user_id]
            del current_request[user_id]
        # Выполняем соответствующее действие
        if callback_data == "update_members":
            update_members(bot, chat_id)
        elif callback_data == "to_main_menu":
            is_private = ("@chat" not in chat_id)
            show_main_menu(bot, chat_id, is_private)
        elif callback_data == "to_requests_menu":
            show_requests_menu(bot, chat_id)
        elif callback_data == "show_your_requests":
            show_request_groups(bot, user_id, chat_id)
        elif callback_data == "show_your_votes":
            show_your_votes(bot, user_id, chat_id)
        return
    
    if callback_data == "to_requests_menu":
        show_requests_menu(bot, chat_id)
        return
    
    if callback_data == "show_your_requests":
        show_request_groups(bot, user_id, chat_id)
        return
    
    if callback_data.startswith("view_requests_group_"):
        group_id = callback_data.replace("view_requests_group_", "")
        show_requests_for_group(bot, user_id, group_id, chat_id)
        return
    
    if callback_data == "show_your_votes":
        show_your_votes(bot, user_id, chat_id)
        return
    
    if callback_data == "to_main_menu":
        is_private = ("@chat" not in chat_id)
        show_main_menu(bot, chat_id, is_private)
        return
    
    if callback_data.startswith("choose_group_"):
        group_id, group_name = decode_from_callback(callback_data)
        if user_id in current_request:
            request_id = current_request[user_id]
            if user_id in pending_requests and request_id in pending_requests[user_id]:
                req = pending_requests[user_id][request_id]
                req["group"] = group_id
                req["group_name"] = group_name
                req["stage"] = "expiry"
                bot.send_text(
                    chat_id = user_id, 
                    text = "Вводи время окончания голосования в одном из следующих форматов:\n"
                        "🔹 HH:MM – сегодня в указанное время\n"
                        "🔹 N – через N минут\n"
                        "🔹 DD.MM HH:MM – указанная дата и время\n"
                        "🔹 DD.MM.YYYY HH:MM – полная дата и время")
        return

    
    if callback_data.startswith("approve_"):
        request_id = callback_data.split("_", 1)[1]
        
        # Проверяем, был ли уже завершён запрос
        if request_id in approval_votes and user_id in approval_votes[request_id]:
            bot.send_text(chat_id=event.from_chat, text="Твой голос уже засчитан")
            return

        approval_votes.setdefault(request_id, {})[user_id] = "принят"
        bot.send_text(chat_id=event.from_chat, text="Запрос одобрен")

        # Получаем данные запроса
        found_request = False
        for requester, req_dict in pending_requests.items():
            if request_id in req_dict:
                requester_id = req_dict[request_id].get("requester_id")
                request_name = req_dict[request_id].get("name", "Без названия")
                group_name = req_dict[request_id].get("group_name")
                
                # Проверяем, завершено ли голосование
                #if not req_dict[request_id].get("vote_finalized", False):
                #    finalize_vote(user_id, request_id, req_dict[request_id].get("group"))
                bot.send_text(
                    chat_id=requester_id, 
                    text=f"Пользователь {user_id} из группы \"{group_name}\" одобрил твой запрос \"{request_name}\""
                )
                found_request = True
                return

        if not found_request:
            logging.error(f"Запрос с request_id {request_id} не найден")
        return

    if callback_data.startswith("reject_"):
        request_id = callback_data.split("_", 1)[1]
        
        # Проверяем, был ли уже завершён запрос
        if request_id in approval_votes and user_id in approval_votes[request_id]:
            bot.send_text(chat_id=event.from_chat, text="Твой голос уже засчитан")
            return

        approval_votes.setdefault(request_id, {})[user_id] = "отклонён"
        bot.send_text(chat_id=event.from_chat, text="Запрос отклонён")

        # Получаем данные запроса
        found_request = False
        for requester, req_dict in pending_requests.items():
            if request_id in req_dict:
                requester_id = req_dict[request_id].get("requester_id")
                request_name = req_dict[request_id].get("name", "Без названия")
                group_name = req_dict[request_id].get("group_name", "Без названия")
                
                # Проверяем, завершено ли голосование
                #if not req_dict[request_id].get("vote_finalized", False):
                #    finalize_vote(user_id, request_id, req_dict[request_id].get("group"))
                bot.send_text(
                    chat_id=requester_id, 
                    text=f"Пользователь {user_id} из группы \"{group_name}\" отклонил твой запрос \"{request_name}\""
                )
                found_request = True
                return

        if not found_request:
            logging.error(f"Запрос с request_id {request_id} не найден")
        return

    show_main_menu(bot, chat_id, chat_id in chat_members)

def handle_message(bot: Bot, event: Any) -> None:
    user_id = event.data.get("from", {}).get("userId", "")
    chat_id = event.from_chat
    chat_type = event.data.get("chat", {}).get("type", "")
    is_private = (chat_type == "private")

    if not is_private or user_id not in pending_requests or not pending_requests[user_id]:
        show_main_menu(bot, chat_id, is_private)
        return

    request_id = current_request.get(user_id)
    if request_id == None:
        show_main_menu(bot, chat_id, is_private)
        return
    req = pending_requests[user_id][request_id]
    text = event.data.get("text", "").strip()
    parts = event.data.get("parts", [])

    stage = req.get("stage", "name")
    if stage == "done" or req == None:
        show_main_menu(bot, chat_id, is_private)
        return

    if stage == "name":
        req["name"] = text
        req["stage"] = "description"
        bot.send_text(chat_id=user_id, text="А как опишем апрув?")
        return

    elif stage == "description":
        req["description"] = text
        req["stage"] = "image"
        bot.send_text(
            chat_id=user_id,
            text="Хочешь прикрепить изображение? Отправь файл или нажми кнопку ниже.",
            inline_keyboard_markup=[[{"text": "Продолжить без изображения", "callbackData": "no_image"}]]
        )
        return

    elif stage == "image":
        # Пользователь отправил файл
        for part in parts:
            if part.get("type") == "file":
                file_id = part.get("payload", {}).get("fileId")
                if file_id:
                    req["image"] = file_id
                    req["stage"] = "group"
                    bot.send_text(chat_id=user_id, text="Изображение прикреплено ✅")
                    show_preview_request(bot, user_id)
                    return

        # Если файл не отправлен — игнорируем
        bot.send_text(chat_id=user_id, text="Прикрепи изображение или нажми \"Продолжить без изображения\"")
        return

    elif stage == "expiry":
        expiry = parse_expiry_time(text)
        if expiry:
            req["expiry"] = expiry.strftime("%Y-%m-%d %H:%M")
            req["stage"] = "done"
            threading.Thread(target=start_vote_timer, args=(
                user_id, request_id, expiry.timestamp(), req["group"]
            )).start()
            send_approval_request(bot, user_id, req["group"], request_id)
        else:
            bot.send_text(chat_id=user_id, text="Неверный формат времени. Попробуй снова!")
        return


def update_members(bot: Bot, chat_id: str) -> None:
    try:
        response = bot.get_chat_members(chat_id).json()
        logging.info(f"Ответ от API (get_chat_members): {response}")
        members = response.get("members", [])
        member_ids = [member.get("userId", "Неизвестно") for member in members]
        chat_info = bot.get_chat_info(chat_id).json()
        group_name = chat_info.get("title", "Неизвестно")
        chat_members[chat_id] = {
            "groupId": chat_id,
            "groupName": group_name,
            "members": member_ids
        }
        logging.info(f"Обновлённый список участников для {chat_id}: {chat_members[chat_id]['members']}")
        bot.send_text(chat_id = chat_id, text = f"Список участников обновлён: {len(member_ids)} человек.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении списка участников: {e}")
        bot.send_text(chat_id = chat_id, text = "Ошибка при обновлении списка участников.")

def handle_member_added(bot: Bot, event: Any) -> None:
    """
    Обработка события добавления пользователя в группу.
    """
    group_id = event.data.get("chat").get("chatId")
    update_members(bot, group_id)  # Обновляем список участников для этой группы

def handle_member_removed(bot: Bot, event: Any) -> None:
    """
    Обработка события удаления пользователя из группы.
    """
    group_id = event.data.get("chat").get("chatId")
    update_members(bot, group_id)  # Обновляем список участников для этой группы

def handle_bot_added_to_group(bot: Bot, event: Any) -> None:
    """
    Обработка события добавления бота в группу.
    """
    group_id = event.data.get("chat").get("chatId")
    update_members(bot, group_id)  # Обновляем список участников для этой группы


# Регистрация обработчиков
bot.dispatcher.add_handler(MessageHandler(callback = handle_message))
bot.dispatcher.add_handler(BotButtonCommandHandler(callback = handle_buttons))
bot.dispatcher.add_handler(CommandHandler(command = "/update_members", callback = update_members))
bot.dispatcher.add_handler(NewChatMembersHandler(callback=handle_member_added))
bot.dispatcher.add_handler(LeftChatMembersHandler(callback=handle_member_removed))


logging.info("Бот запущен и ожидает сообщений...")
bot.start_polling()
bot.idle()
