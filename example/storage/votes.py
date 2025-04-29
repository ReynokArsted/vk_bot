from uuid import UUID
from typing import List, Tuple
from example.storage.database import get_db
from contextlib import closing
from example.storage.models import Vote

def add_vote(request_id: UUID, user_id: str, vote: str) -> None:
    with closing(next(get_db())) as db:
        existing = db.query(Vote).filter_by(request_id=request_id, user_id=user_id).first()
        if existing:
            existing.vote = vote
        else:
            new_vote = Vote(request_id=request_id, user_id=user_id, vote=vote)
            db.add(new_vote)
        db.commit()

def get_vote(request_id: str, user_id: str) -> str:
    with closing(next(get_db())) as db:
        vote = db.query(Vote).filter(Vote.request_id == request_id, Vote.user_id == user_id).first()
        return vote.vote if vote else None

def get_votes(request_id: UUID) -> List[Vote]:
    with closing(next(get_db())) as db:
        return db.query(Vote).filter_by(request_id=request_id).all()

