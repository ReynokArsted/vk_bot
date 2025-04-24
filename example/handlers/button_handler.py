from bot.bot import Bot
from example.storage import pending_requests, current_request, approval_votes, chat_members
from example.logger import logging
from example.features.requests import show_preview_request, show_available_groups
from example.features.groups import update_members
from example.main_menu import show_main_menu
from example.requests_menu import show_requests_menu, show_requests_for_group, show_your_votes
from example.features.requests import show_request_groups
from example.utils import decode_from_callback
from typing import Any
import uuid

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
