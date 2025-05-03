from example.features.requests import (
    show_preview_request, 
    show_available_groups
)
from example.features.groups import update_members
from example.storage.group_members import get_group_name
from example.main_menu import show_main_menu
from example.utils import create_inline_keyboard
from example.requests_menu import (
    show_requests_menu, 
    show_your_votes, 
    show_requests_for_group
)
from example.features.requests import (
    show_request_groups 
)
from example.storage.requests import (
    create_draft,
    get_draft,
    update_draft,
    get_request,
    delete_draft
)
from example.storage.votes import get_vote, add_user_to_voted_list
from example.storage.group_members import is_user_in_group
from example.handlers.remind_handler import handle_set_reminder_frequency, handle_reminder_settings

def handle_buttons(bot, event):
    from example.utils import decode_from_callback

    callback_data = event.data.get("callbackData", "")
    chat_id = event.from_chat
    user_id = event.data.get("from", {}).get("userId", "")
    is_private = ("@chat" not in chat_id)

    draft = get_draft(user_id)

    # Отмена загрузки изображения
    if callback_data == "no_image" and draft:
        update_draft(draft.id, image_file_id=None, stage="group")
        show_preview_request(bot, user_id)
        return

    # Подтвердить превью
    if callback_data == "preview_ok" and draft:
        show_available_groups(bot, user_id)
        return

    # Редактировать превью
    if callback_data == "preview_edit" and draft:
        update_draft(draft.id, name=None, description=None, image_file_id=None, group_id=None, group_name=None, expiry=None, stage="name", vote_finalized=False)
        bot.send_text(chat_id=user_id, text="Начнём редактирование. Введи название запроса:")
        return

    # Создать новый запрос
    if callback_data == "create_approval_request":
        draft_id = create_draft(user_id)
        bot.send_text(chat_id=user_id, text="Как назовём запрос на апрув?")
        return

    if callback_data in {"to_main_menu", "update_members", "to_requests_menu", 
                        "show_your_requests", "show_your_votes", "settings_reminder_frequency",
                        "set_reminder_15", "set_reminder_25", "set_reminder_30", "set_reminder_60"}:
        delete_draft(user_id)
        if callback_data == "update_members":
            update_members(bot, chat_id)
        elif callback_data == "to_main_menu":
            show_main_menu(bot, chat_id, is_private)
        elif callback_data == "to_requests_menu":
            show_requests_menu(bot, chat_id)
        elif callback_data == "show_your_requests":
            show_request_groups(bot, user_id, chat_id)
        elif callback_data == "show_your_votes":
            show_your_votes(bot, user_id, chat_id)
        elif callback_data == "settings_reminder_frequency":
            handle_reminder_settings(bot, user_id)
        elif callback_data == "set_reminder_15":
            handle_set_reminder_frequency(bot, user_id, 15)
        elif callback_data == "set_reminder_25":
            handle_set_reminder_frequency(bot, user_id, 25)
        elif callback_data == "set_reminder_30":
            handle_set_reminder_frequency(bot, user_id, 30)
        elif callback_data == "set_reminder_60":
            handle_set_reminder_frequency(bot, user_id, 60)
        return

    # Выбор группы из списка
    if callback_data.startswith("choose_group_") and draft:
        group_id, group_name = decode_from_callback(callback_data)
        update_draft(draft.id, group_id=group_id, group_name=group_name, stage="expiry")
        bot.send_text(
            chat_id=user_id,
            text="Вводи время окончания голосования в одном из следующих форматов:\n"
                "🔹 HH:MM – сегодня в указанное время\n"
                "🔹 N – через N минут\n"
                "🔹 DD.MM HH:MM – указанная дата и время\n"
                "🔹 DD.MM.YYYY HH:MM – полная дата и время"
        )
        return

    if callback_data.startswith("approve_") or callback_data.startswith("reject_"):
        action, request_id = callback_data.split("_", 1)
        req = get_request(request_id)
        if not req:
            bot.send_text(chat_id=event.from_chat, text="Запрос не найден")
            return

        # Проверка, что пользователь в нужной группе
        if not is_user_in_group(req.group_id, user_id):
            bot.send_text(chat_id=event.from_chat, text="Ты не состоишь в группе, связанной с этим запросом")
            return

        # Добавление голоса пользователя
        vote_type = "approved" if action == "approve" else "rejected"
        add_user_to_voted_list(request_id, user_id, vote_type)

        # Отправляем ответ
        if vote_type == "approved":
            bot.send_text(chat_id=event.from_chat, text=f"Запрос принят")
            if user_id != req.requester_id:
                bot.send_text(
                    chat_id=req.requester_id,
                    text=f"Пользователь {user_id} из группы \"{req.group_name}\" принял твой запрос \"{req.name}\""
                )
        else:
            bot.send_text(chat_id=event.from_chat, text=f"Запрос отклонён")
            if user_id != req.requester_id:
                bot.send_text(
                    chat_id=req.requester_id,
                    text=f"Пользователь {user_id} из группы \"{req.group_name}\" отклонил твой запрос \"{req.name}\""
                )
        return


    if callback_data.startswith("view_requests_group_"):
        group_id = callback_data.removeprefix("view_requests_group_")
        show_requests_for_group(bot, user_id, group_id, chat_id)
        return
    
    if callback_data.startswith("view_request:"):
        request_id = callback_data.split(":", 1)[1]
        req = get_request(request_id)
        if not req:
            bot.send_text(chat_id=chat_id, text="Запрос не найден")
            return

        text = f"📄 Название запроса:\n<b>{req.name or 'Без названия'}</b>\n\n"
        if req.description:
            text += f"Описание: {req.description}\n\n"
        text += f"👤 Создатель: {req.requester_id}\n"
        text += f"👥 Группа: {req.group_name or get_group_name(req.group_id)}\n"

        print(f"[DRBUG] {req.status}")
        if req.status == "аpproved":
            text += f"🗳 Статус: принят"
        elif req.status == "rejected":
            text += f"🗳 Статус: отклонён"
        elif req.status == "undecided":
            text += f"🗳 Статус: не решено"
        elif req.status == "in_progress":
            text += f"🗳 Статус: в процессе голосования"

        buttons = [[{"text": "Назад", "callbackData": f"back_to_group_{req.group_id}"}]]

        if req.status == "in_progress":
            existing_vote = get_vote(request_id, user_id)
            if not existing_vote:
                buttons.insert(0, [
                    {"text": "👍 Одобрить", "callbackData": f"approve_{request_id}"},
                    {"text": "👎 Отклонить", "callbackData": f"reject_{request_id}"}
                ])

        if req.image_file_id:
            bot.send_file(
                chat_id=chat_id,
                file_id=req.image_file_id,
                caption=text,
                parse_mode="HTML",
                inline_keyboard_markup=create_inline_keyboard(buttons)
            )
        else:
            bot.send_text(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                inline_keyboard_markup=create_inline_keyboard(buttons)
            )
        return
    
    if callback_data.startswith("back_to_group_"):
        group_id = callback_data.split("_", 3)[3]
        show_requests_for_group(bot, user_id, group_id, chat_id)
        return
    
    show_main_menu(bot, chat_id, is_private)
