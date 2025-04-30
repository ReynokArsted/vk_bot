from uuid import UUID
from typing import List
from example.storage.database import get_db
from contextlib import closing
from example.storage.models import Vote
from example.storage.requests import get_request

def add_vote(request_id: UUID, user_id: str, vote: str) -> None:
    with closing(next(get_db())) as db:
        existing = db.query(Vote).filter_by(request_id=request_id, user_id=user_id).first()
        if existing:
            existing.vote = vote
            print(f"\n[UPDATE] Голос обновлён: {user_id} -> {vote}\n")
        else:
            new_vote = Vote(request_id=request_id, user_id=user_id, vote=vote)
            db.add(new_vote)
            print(f"\n[UPDATE] Голос сохранён: {user_id} -> {vote}\n")
        db.commit()

def get_vote(request_id: str, user_id: str) -> str:
    with closing(next(get_db())) as db:
        vote = db.query(Vote).filter(Vote.request_id == request_id, Vote.user_id == user_id).first()
        print(f"\n[GET] Голос для {user_id} по запросу {request_id}: {'найден' if vote else 'нет'}\n")
        return vote.vote if vote else None

def get_votes(request_id: UUID) -> List[Vote]:
    with closing(next(get_db())) as db:
        return db.query(Vote).filter_by(request_id=request_id).all()

def add_user_to_voted_list(request_id: UUID, user_id: str, vote_type: str):
    """
    Добавляет голос пользователя по запросу в таблицу голосов
    """
    # Получаем запрос по ID
    req = get_request(request_id)
    if not req:
        return  # Запрос не найден, ничего не делаем

    with closing(next(get_db())) as db:
        # Проверяем, проголосовал ли уже пользователь по этому запросу
        existing_vote = db.query(Vote).filter_by(request_id=request_id, user_id=user_id).first()
        if existing_vote:
            return

        # Добавляем новый голос в таблицу
        new_vote = Vote(request_id=request_id, user_id=user_id, vote=vote_type)
        db.add(new_vote)
        db.commit()

        return new_vote
