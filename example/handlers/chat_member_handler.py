from bot.bot import Bot
from typing import Any
from example.features.groups import update_members

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