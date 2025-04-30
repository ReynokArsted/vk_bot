from bot.bot import Bot
from example.utils import create_inline_keyboard
from example.storage.requests import get_requests_by_group, get_votes_by_user, get_request
from example.storage.group_members import get_group_name

def show_requests_menu(bot: Bot, chat_id: str) -> None:
    text = "Статус запросов в группах"
    buttons = [
        [{"text": "Список запросов", "callbackData": "show_your_requests"}],
        [{"text": "Ваши голосования", "callbackData": "show_your_votes"}],
        [{"text": "Назад в главное меню", "callbackData": "to_main_menu"}],
    ]
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=create_inline_keyboard(buttons))

def show_requests_for_group(bot: Bot, user_id: str, group_id: str, chat_id: str) -> None:
    requests = get_requests_by_group(group_id)
    group_name = get_group_name(group_id)
    buttons = []

    for req in requests:
        buttons.append([{
            "text": req["name"] or "Без названия",
            "callbackData": f"view_request:{req['id']}"
        }])

    if not buttons:
        bot.send_text(chat_id=chat_id, text=f'В группе "{group_name}" нет активных запросов')
        return

    buttons.append([{"text": "Назад", "callbackData": "show_your_requests"}])
    bot.send_text(
        chat_id=chat_id,
        text=f'Запросы в группе "{group_name}":',
        inline_keyboard_markup=create_inline_keyboard(buttons)
    )


def show_your_votes(bot: Bot, user_id: str, chat_id: str) -> None:
    user_votes = get_votes_by_user(user_id)
    votes_info = []

    for req_id, status in user_votes.items():
        req = get_request(req_id)
        if req:
            group_name = req.group_name
            votes_info.append(f'Запрос "{req.name}" от {req.requester_id} (группа: {group_name}) — {status}')
        else:
            votes_info.append(f"Запрос {req_id} — информация не найдена")

    if not votes_info:
        bot.send_text(chat_id=chat_id, text="У тебя пока нет голосований")
    else:
        bot.send_text(chat_id=chat_id, text="\n\n".join(votes_info))
