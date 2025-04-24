from bot.bot import Bot
from example.bot_instance import bot
from example.main_menu import show_main_menu
from example.storage import pending_requests, chat_members, current_request, approval_votes
from example.utils import create_inline_keyboard, encode_for_callback
from example.logger import logging
import time

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

def start_vote_timer(user_id: str, request_id: str, deadline: float, group_id: str) -> None:
    sleep_duration = deadline - time.time()
    if sleep_duration > 0:
        time.sleep(sleep_duration)
    finalize_vote(user_id, request_id, group_id)    


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

def finalize_vote(user_id: str, request_id: str, group_id: str) -> None:
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

    # Проверка наличия изображения
    image_file_id = request_data.get("image")
    
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