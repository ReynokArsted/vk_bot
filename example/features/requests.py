from example.utils import create_inline_keyboard, encode_for_callback
from example.logger import logging
from example.main_menu import show_main_menu
from example.storage.requests import (
    get_request, 
    get_draft, 
    get_requests_by_user,
    finalize_draft,
    update_request_status
)
from example.storage.group_members import (
    get_group_members, 
    get_group_name, 
    get_user_display_name, 
    get_user_groups
)
from example.storage.votes import get_votes
from bot.bot import Bot
from example.bot_instance import bot
import time

def send_approval_request(bot: Bot, user_id: str, group_id: str, request_id: str) -> None:
    members = get_group_members(group_id)
    req = get_draft(user_id)
    if not req or not members:
        logging.error(f"Не удалось отправить запрос: request={req}, members={members}")
        return

    text = f"📢 Новый запрос на апрув!\n\n" \
        f"📌 Название: {req.name}\n" \
        f"📝 Описание:\n{req.description}\n\n" \
        f"👤 Отправитель: {user_id}\n" \
        f"👥 Группа: {get_group_name(group_id)}\n" \
        f"⏳ До: {req.expiry or 'не указано'}"

    buttons = [
        [{"text": "✅ Одобрить", "callbackData": f"approve_{request_id}"}],
        [{"text": "❌ Отклонить", "callbackData": f"reject_{request_id}"}]
    ]

    bot.send_text(chat_id=user_id, text="✅ Запрос отправлен!")
    for member_id in members:
        if req.image_file_id:
            bot.send_file(
                chat_id=member_id,
                file_id=req.image_file_id,
                caption=text,
                inline_keyboard_markup=create_inline_keyboard(buttons)
            )
        else:
            bot.send_text(
                chat_id=member_id,
                text=text,
                inline_keyboard_markup=create_inline_keyboard(buttons)
            )
    finalize_draft(request_id)

def start_vote_timer(user_id: str, request_id: str, deadline: float, group_id: str) -> None:
    sleep_duration = deadline - time.time()
    if sleep_duration > 0:
        time.sleep(sleep_duration)
    finalize_vote(user_id, request_id, group_id)

def finalize_vote(user_id: str, request_id: str, group_id: str) -> None:
    req = get_request(request_id)
    if not req or req.stage == "finalized":
        return

    votes = {v.user_id: v.vote for v in get_votes(request_id)}
    members = get_group_members(group_id)
    member_names = {uid: get_user_display_name(uid) for uid in members}

    approved_users = [uid for uid, v in votes.items() if v in ("approved", "принят")]
    rejected_users = [uid for uid, v in votes.items() if v in ("rejected", "отклонён")]
    non_voters = [uid for uid in members if uid not in votes]

    approved_names = ", ".join(member_names[uid] for uid in approved_users) or "никто"
    rejected_names = ", ".join(member_names[uid] for uid in rejected_users) or "никто"
    non_voter_names = ", ".join(member_names[uid] for uid in non_voters) or "никто"

    approved_count = len(approved_users)
    rejected_count = len(rejected_users)
    
    if approved_count > rejected_count:
        result_text = "Итог - ✅ Запрос одобрен!"
        update_request_status(request_id, "approved")  # Запрос принят
    elif rejected_count > approved_count:
        result_text = "Итог - ❌ Запрос отклонён!"
        update_request_status(request_id, "rejected")  # Запрос отклонён
    else:
        result_text = "Итог - 🤷 Голоса разделились и решение не принято"
        update_request_status(request_id, "undecided")  # Ничья (или недостаточно голосов)


    summary = (
        f"Голосование по запросу \"{req.name}\" в группе \"{get_group_name(group_id)}\" завершено!\n\n"
        f"✅ За ({approved_count}): {approved_names}\n"
        f"❌ Против ({rejected_count}): {rejected_names}\n"
        f"❔ Не голосовали: {non_voter_names}\n\n"
        f"{result_text}"
    )

    for member_id in members:
        if req.image_file_id:
            bot.send_file(chat_id=member_id, file_id=req.image_file_id, caption=summary)
        else:
            bot.send_text(chat_id=member_id, text=summary)

def show_preview_request(bot: Bot, user_id: str) -> None: 
    req = get_draft(user_id)
    if not req:
        print(f"\n !!! 222 : {req}\n")
        return

    text = f"**Предпросмотр запроса**\n\n" \
        f"📢 Новый запрос на апрув!\n\n" \
        f"📌 Название: {req.name}\n" \
        f"📝 Описание: {req.description}"

    keyboard = create_inline_keyboard([
        [{"text": "✅ Всё верно", "callbackData": "preview_ok"}],
        [{"text": "✏️ Изменить", "callbackData": "preview_edit"}]
    ])

    if req.image_file_id:
        bot.send_file(chat_id=user_id, file_id=req.image_file_id, caption=text, inline_keyboard_markup=keyboard)
    else:
        bot.send_text(chat_id=user_id, text=text, inline_keyboard_markup=keyboard)

def show_request_groups(bot: Bot, user_id: str, chat_id: str) -> None:
    user_group_ids = get_user_groups(user_id)
    groups = {group_id: get_group_name(group_id) for group_id in user_group_ids}
    
    if not groups:
        bot.send_text(chat_id=chat_id, text="У тебя пока нет активных групп")
        return

    buttons = [
        [{"text": group_name, "callbackData": f"view_requests_group_{group_id}"}]
        for group_id, group_name in groups.items()
    ]
    buttons.append([{"text": "Назад", "callbackData": "to_requests_menu"}])

    bot.send_text(chat_id=chat_id, text="Выбери группу, для которой хочешь посмотреть запросы", inline_keyboard_markup=create_inline_keyboard(buttons))

def show_request_details(bot: Bot, user_id: str, chat_id: str, request_id: str) -> None:
    req = get_request(request_id)
    if not req:
        bot.send_text(chat_id=chat_id, text="Запрос не найден")
        return

    text = (
        f"📌 Название: *{req.name or 'Без названия'}*\n"
        f"📝 Описание: {req.description or '—'}\n"
        f"📎 Группа: {req.group_name or 'не указана'}\n"
        f"📅 Статус: {req.status}\n"
    )

    buttons = [[{"text": "Назад", "callbackData": f"view_requests_group_{req.group_id}"}]]
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))


def show_available_groups(bot: Bot, user_id: str) -> None:
    group_ids = get_user_groups(user_id)

    groups = [
        {"groupId": gid, "groupName": get_group_name(gid)}
        for gid in group_ids
    ]

    if not groups:
        bot.send_text(chat_id=user_id, text="Этого бота нет в группах, в которых ты состоишь")
        return

    buttons = [
        [{"text": g["groupName"], "callbackData": encode_for_callback(g["groupId"], g["groupName"])}]
        for g in groups
    ]

    bot.send_text(
        chat_id=user_id,
        text="Выбирай группу для отправки запроса",
        inline_keyboard_markup=create_inline_keyboard(buttons)
    )
