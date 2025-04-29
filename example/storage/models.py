import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, Text, Integer, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base

class Request(Base):
    __tablename__ = "requests"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id   = Column(String, nullable=False)
    name           = Column(String, nullable=True)
    description    = Column(String, nullable=True)
    group_id       = Column(String, nullable=True)
    group_name     = Column(String, nullable=True)
    expiry         = Column(DateTime, nullable=True)
    image_file_id  = Column(String, nullable=True)
    vote_finalized = Column(Boolean, default=False)
    stage          = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    status = Column(String, default="in_progress")

    votes = relationship("Vote", back_populates="request", cascade="all, delete-orphan")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(UUID(as_uuid=True), ForeignKey('requests.id', ondelete='CASCADE'), nullable=False)
    vote = Column(String, nullable=False)
    user_id = Column(String, nullable=False)

    request = relationship("Request", back_populates="votes")

class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_user'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class CurrentRequest(Base):
    __tablename__ = "current_requests"

    # Поля полностью повторяют Request, только другой tablename
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id   = Column(String, nullable=False)
    name           = Column(String, nullable=True)
    description    = Column(String, nullable=True)
    group_id       = Column(String, nullable=True)
    group_name     = Column(String, nullable=True)
    expiry         = Column(DateTime, nullable=True)
    image_file_id  = Column(String, nullable=True)
    vote_finalized = Column(Boolean, default=False)
    stage          = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())


class Group(Base):
    __tablename__ = "groups"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
