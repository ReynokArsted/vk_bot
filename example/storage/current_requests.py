from uuid import UUID
from .db import get_db
from contextlib import closing
from .models import CurrentRequest

def get_current_request(user_id: str) -> str:
    with closing(next(get_db())) as db:
        current_request = db.query(CurrentRequest).filter_by(user_id=user_id).first()
        return current_request.current_request_id if current_request else None

def set_current_request(user_id: str, request_id: UUID) -> None:
    with closing(next(get_db())) as db:
        cr = db.query(CurrentRequest).filter_by(user_id=user_id).first()
        if cr:
            cr.current_request_id = request_id
        else:
            cr = CurrentRequest(user_id=user_id, current_request_id=request_id)
            db.add(cr)
        db.commit()

def delete_current_request(user_id: str) -> None:
    with closing(next(get_db())) as db:
        cr = db.query(CurrentRequest).filter_by(user_id=user_id).first()
        if cr:
            db.delete(cr)
            db.commit()
