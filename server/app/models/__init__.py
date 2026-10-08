from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="projects")
    notes = relationship("Note", back_populates="project", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    # 为空表示"未整理"池中的语音
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=True)
    audio_path = Column(String(256), nullable=False)
    text = Column(Text, default="")
    duration = Column(Float, default=0.0)
    sort_order = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="notes")
    annotations = relationship("Annotation", back_populates="note", cascade="all, delete-orphan")


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    note_id = Column(Integer, ForeignKey("notes.id"), index=True, nullable=False)
    type = Column(String(16), nullable=False)  # "text" | "image"
    content = Column(Text, nullable=False)     # 文字内容 或 图片文件路径
    created_at = Column(DateTime, default=datetime.utcnow)

    note = relationship("Note", back_populates="annotations")
