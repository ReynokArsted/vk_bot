from bot.bot import Bot
from example.logger import logging
from typing import Any
from example.storage.database import SessionLocal
from example.storage.models import Group, GroupMember

def handle_member_added(bot: Bot, event: Any) -> None:
    """
    Обработка события добавления пользователя в группу
    """
    group_id = event.data.get("chat").get("chatId")
    update_members(bot, group_id)  # Обновляем список участников для этой группы

def handle_member_removed(bot: Bot, event: Any) -> None:
    """
    Обработка события удаления пользователя из группы
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
        members = response.get("members", [])
        member_ids = [member.get("userId") for member in members if member.get("userId")]

        chat_info = bot.get_chat_info(chat_id).json()
        group_name = chat_info.get("title", "Неизвестно")

        with SessionLocal() as session:
            # Обновляем или создаём группу
            group = session.query(Group).filter_by(id=chat_id).first()
            if not group:
                group = Group(id=chat_id, name=group_name)
                session.add(group)
            else:
                group.name = group_name

            # Удаляем старых участников
            session.query(GroupMember).filter_by(group_id=chat_id).delete()

            # Добавляем новых участников, сохраняя их имена
            for member in members:
                user_id = member.get("userId")
                user_name = member.get("firstName", "") + " " + member.get("lastName", "")
                if user_id:
                    session.add(GroupMember(group_id=chat_id, user_id=user_id, user_name=user_name.strip()))

            session.commit()

        bot.send_text(chat_id=chat_id, text=f"Список участников обновлён: {len(member_ids)} человек")
    except Exception as e:
        logging.error(f"Ошибка при обновлении списка участников: {e}")
        bot.send_text(chat_id=chat_id, text="Ошибка при обновлении списка участников")
