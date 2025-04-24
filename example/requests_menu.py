from bot.bot import Bot
from example.storage import pending_requests, chat_members, approval_votes
from example.utils import create_inline_keyboard

def show_requests_menu(bot: Bot, chat_id: str) -> None:
    text = "Статус запросов"
    buttons = [
        [{"text": "Список ваших запросов", "callbackData": "show_your_requests"}],
        [{"text": "Ваши голосования", "callbackData": "show_your_votes"}],
        [{"text": "Назад в главное меню", "callbackData": "to_main_menu"}],
    ]
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))

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


