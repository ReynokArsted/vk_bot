from example.main_menu import show_main_menu
from example.features.requests import show_preview_request, send_approval_request, start_vote_timer
from example.utils import parse_expiry_time
from example.storage.database import get_db
from example.storage.requests import (
    get_draft,
    update_draft,
)
import threading

def handle_message(bot, event):
    user_id = event.data.get("from", {}).get("userId", "")
    chat_id = event.from_chat
    chat_type = event.data.get("chat", {}).get("type", "")
    is_private = (chat_type == "private")

    # Ничего не делаем, если не в личке
    if not is_private:
        show_main_menu(bot, chat_id, False)
        return

    # Получаем черновик из БД
    draft = get_draft(user_id)

    # Если нет черновика – показываем меню
    if draft is None:
        show_main_menu(bot, chat_id, True)
        return

    text = event.data.get("text", "").strip()
    parts = event.data.get("parts", [])

    # Этап ввода названия
    if draft.stage == "name":
        update_draft(draft.id, name=text, stage="description")
        bot.send_text(chat_id=user_id, text="А как опишем апрув?")
        return

    # Этап ввода описания
    if draft.stage == "description":
        update_draft(draft.id, description=text, stage="image")
        bot.send_text(
            chat_id=user_id,
            text="Хочешь прикрепить изображение? Отправь файл или нажми кнопку ниже.",
            inline_keyboard_markup=[[{"text": "Продолжить без изображения", "callbackData": "no_image"}]]
        )
        return

    # Этап загрузки изображения
    if draft.stage == "image":
        for part in parts:
            if part.get("type") == "file":
                file_id = part.get("payload", {}).get("fileId")
                if file_id:
                    update_draft(draft.id, image_file_id=file_id, stage="group")
                    bot.send_text(chat_id=user_id, text="Изображение прикреплено ✅")
                    show_preview_request(bot, user_id)
                    return
        bot.send_text(chat_id=user_id, text="Прикрепи изображение или нажми \"Продолжить без изображения\"")
        return

    # Этап выбора группы
    if draft.stage == "group":
        # Выбор группы через кнопки – здесь ничего, переходим на preview
        show_preview_request(bot, user_id)
        return

    # Этап выбора времени
    if draft.stage == "expiry":
        expiry = parse_expiry_time(text)
        if expiry:
            update_draft(draft.id, expiry=expiry.strftime("%Y-%m-%d %H:%M"), stage="done")
            # Запускаем таймер
            threading.Thread(
                target=start_vote_timer,
                args=(user_id, draft.id, expiry.timestamp(), draft.group_id)
            ).start()
            send_approval_request(bot, user_id, draft.group_id, draft.id)
        else:
            bot.send_text(chat_id=user_id, text="Неверный формат времени. Попробуй снова!")
        return