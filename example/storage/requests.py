import uuid
from uuid import UUID
from typing import Optional
from datetime import datetime
from contextlib import closing
from example.storage.database import get_db
from example.storage.models import Request, Vote, CurrentRequest

def create_request(requester_id: str) -> UUID:
    with closing(next(get_db())) as db:
        req = Request(requester_id=requester_id)
        db.add(req)
        db.commit()
        db.refresh(req)
        return req.id

def update_request(
    request_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    group_id: Optional[str] = None,
    group_name: Optional[str] = None,
    expiry: Optional[datetime] = None,
    image_file_id: Optional[str] = None,
    vote_finalized: Optional[bool] = None,
    stage: Optional[str] = None
) -> None:
    with closing(next(get_db())) as db:
        req = db.query(Request).filter(Request.id == request_id).first()
        if req is None:
            raise KeyError(f"Request {request_id} not found")
        for field, value in dict(
            name=name,
            description=description,
            group_id=group_id,
            group_name=group_name,
            expiry=expiry,
            image_file_id=image_file_id,
            vote_finalized=vote_finalized
        ).items():
            if value is not None:
                setattr(req, field, value)
        db.commit()

def update_request_status(request_id: UUID, status: str) -> None:
    with closing(next(get_db())) as db:
        req = db.query(Request).filter(Request.id == request_id).first()
        if req:
            req.status = status
            db.commit()
        else:
            raise KeyError(f"Request {request_id} not found")

def get_request(request_id: str) -> Optional[Request]:
    with closing(next(get_db())) as db:
        return db.query(Request).filter(Request.id == request_id).first()

def get_draft(user_id: str) -> Optional[CurrentRequest]:
    with closing(next(get_db())) as db:
        return db.query(CurrentRequest).filter_by(requester_id=user_id).first()


def get_draft_id_for_user(user_id: str):
    """
    Получить последний request_id для пользователя.
    """
    with closing(next(get_db())) as db:
        request = (
            db.query(CurrentRequest)
            .filter(CurrentRequest.requester_id == str(user_id))
            .order_by(CurrentRequest.created_at.desc())
            .first()
        )

        if request:
            return request.id
        return None

def get_requests_by_user(user_id: str) -> list[dict]:
    """Вернуть список запросов, созданных пользователем"""
    with closing(next(get_db())) as db:
        requests = db.query(Request).filter(Request.requester_id == str(user_id)).all()
        result = []
        for req in requests:
            result.append({
                "id": req.id,
                "name": req.name,
                "group_id": req.group_id,
                "requester_id": req.requester_id,
                "group_name": req.group_name,
                "status": req.status,
            })
        return result

def get_drafts_by_user(user_id: str) -> list[dict]:
    """Вернуть список запросов, созданных пользователем"""
    with closing(next(get_db())) as db:
        requests = db.query(CurrentRequest).filter(CurrentRequest.requester_id == str(user_id)).all()
        result = []
        for req in requests:
            result.append({
                "id": req.id,
                "name": req.name,
                "group_id": req.group_id,
                "requester_id": req.requester_id,
                "group_name": req.group_name,
                "status": req.status,
            })
        return result
    
def get_requests_by_group(group_id: str) -> list[dict]:
    """Вернуть список всех запросов в группе"""
    with closing(next(get_db())) as db:
        requests = db.query(Request).filter(Request.group_id == group_id).all()
        result = []
        for req in requests:
            result.append({
                "id": req.id,
                "name": req.name,
                "group_id": req.group_id,
                "requester_id": req.requester_id,
                "group_name": req.group_name,
                "status": req.status,
            })
        return result

def get_votes_by_user(user_id: str) -> dict[str, str]:
    """Вернуть словарь {request_id: статус голоса} для пользователя"""
    with closing(next(get_db())) as db:
        votes = db.query(Vote).filter(Vote.user_id == user_id).all()
        result = {}
        for vote in votes:
            result[vote.request_id] = vote.vote
        return result

def set_current_request(user_id: str, request_id: str) -> None:
    """Установить текущий черновик-запрос для пользователя"""
    with closing(next(get_db())) as db:
        record = db.query(CurrentRequest).filter_by(user_id=user_id).first()
        if record:
            record.current_request_id = request_id  # Исправлено на current_request_id
        else:
            record = CurrentRequest(user_id=user_id, current_request_id=request_id)  # Исправлено на current_request_id
            db.add(record)
        db.commit()


def get_current_request(user_id: str):
    with closing(next(get_db())) as db:
        record = db.query(CurrentRequest).filter_by(user_id=user_id).first()
        return record.current_request_id if record else None


def delete_current_request(user_id: str) -> None:
    """Удалить текущий черновик-запрос пользователя"""
    with closing(next(get_db())) as db:
        db.query(CurrentRequest).filter_by(user_id=user_id).delete()
        db.commit()

def create_draft(requester_id: str) -> str:
    """
    Создаёт новый черновик запроса для пользователя
    """
    with closing(next(get_db())) as db:
        draft = CurrentRequest(
            id=uuid.uuid4(),
            requester_id=requester_id,
            name=None,
            description=None,
            group_id=None,
            group_name=None,
            expiry=None,
            image_file_id=None,
            vote_finalized=False,
            stage="name"
        )
        db.add(draft)
        db.commit()
        return draft.id

def update_draft(draft_id: str, **fields) -> None:
    """
    Обновляет поля существующего черновика
    """
    with closing(next(get_db())) as db:
        db.query(CurrentRequest).filter_by(id=draft_id).update(fields)
        db.commit()


def delete_draft(user_id: str) -> None:
    """
    Удаляет черновик пользователя (отмена процесса создания)
    """
    with closing(next(get_db())) as db:
        db.query(CurrentRequest).filter_by(requester_id=str(user_id)).delete()
        db.commit()


def finalize_draft(draft_id: str) -> None:
    """
    Переносит завершённый черновик из current_requests в основную таблицу requests.
    После копирования удаляет черновик
    """
    with closing(next(get_db())) as db:
        draft = db.query(CurrentRequest).filter_by(id=draft_id).first()
        if not draft:
            return

        # Копируем поля в новую запись Request
        req = Request(
            id=draft.id,
            requester_id=draft.requester_id,
            name=draft.name,
            description=draft.description,
            group_id=draft.group_id,
            group_name=draft.group_name,
            expiry=draft.expiry,
            image_file_id=draft.image_file_id,
            created_at=draft.created_at,
            vote_finalized=draft.vote_finalized,
            stage=draft.stage
        )
        db.add(req)
        db.delete(draft)
        db.commit()
