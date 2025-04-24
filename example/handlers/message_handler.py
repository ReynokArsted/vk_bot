from example.storage import pending_requests, current_request
from example.main_menu import show_main_menu
from example.features.requests import show_preview_request, send_approval_request, start_vote_timer
from example.utils import parse_expiry_time
import threading

def handle_message(bot, event):
    user_id = event.data.get("from", {}).get("userId", "")
    chat_id = event.from_chat
    # Логика обработки сообщений (включая создание запросов, голосование и т.д.)
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