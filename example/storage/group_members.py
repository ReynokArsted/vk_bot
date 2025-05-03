from typing import List
from example.storage.database import get_db
from example.storage.models import GroupMember, User, Group
from contextlib import closing
from example.bot_instance import BOT_ID

def is_user_in_group(group_id: str, user_id: str) -> bool:
    """
    Проверяет, является ли пользователь членом группы
    """
    with closing(next(get_db())) as db:
        member = db.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
        return member is not None


def set_group_members(group_id: str, members: List[dict]) -> None:
    with closing(next(get_db())) as db:
        db.query(GroupMember).filter_by(group_id=group_id).delete()
        for member in members:
            gm = GroupMember(
                group_id=group_id,
                user_id=member.get('userId'),
                user_name=member.get('name')
            )
            db.add(gm)
        db.commit()

def get_group_members(group_id: str) -> List[str]:
    with closing(next(get_db())) as db:
        members = db.query(GroupMember).filter_by(group_id=group_id).all()
        return [m.user_id for m in members if m.user_id != BOT_ID]

def get_group_name(group_id: str) -> str:
    with closing(next(get_db())) as db:
        group = db.query(Group).filter_by(id=group_id).first()
        return group.name if group else f"[группа {group_id}]"

def get_user_groups(user_id: str) -> List[str]:
    with closing(next(get_db())) as db:
        rows = db.query(GroupMember).filter_by(user_id=user_id).all()
        return [gm.group_id for gm in rows]

def format_user_list(users: list[str]) -> str:
    """Форматирует список пользователей: имена через запятую, каждый с новой строки"""
    return ",\n".join(users) if users else "никто"