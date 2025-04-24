from bot.bot import Bot
from example.logger import logging
from typing import Any
from example.storage import chat_members

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

