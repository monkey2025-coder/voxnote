from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Index, text
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


class SandboxApp(Base):
    """一个占用固定沙箱槽位的应用。槽位由 container + container_port 唯一确定。"""

    __tablename__ = "sandbox_apps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=True)
    name = Column(String(128), nullable=False)
    slot_key = Column(String(32), nullable=False, index=True)
    container = Column(String(64), nullable=False)
    container_port = Column(Integer, nullable=False)
    host_port = Column(Integer, nullable=False)
    workdir = Column(String(256), nullable=False)
    session_id = Column(String(64), nullable=False, default="")
    status = Column(String(16), nullable=False, default="active", index=True)
    last_job_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 同一个槽位只允许存在一个活跃应用；软删除后可以复用同一槽位
    __table_args__ = (
        Index(
            "uq_sandbox_active_slot",
            "container",
            "container_port",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )


class AgentJob(Base):
    """一次「把语音交给 Agent 上线应用」的执行记录。"""

    __tablename__ = "agent_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    note_id = Column(Integer, ForeignKey("notes.id"), index=True, nullable=False)
    app_id = Column(Integer, ForeignKey("sandbox_apps.id"), index=True, nullable=True)
    app_name = Column(String(128), nullable=False, default="")
    status = Column(String(16), nullable=False, default="waiting_text", index=True)
    instruction = Column(Text, nullable=False, default="")
    run_id = Column(String(64), nullable=False, default="")
    session_id = Column(String(64), nullable=False, default="")
    answer = Column(Text, nullable=True)
    app_url = Column(String(256), nullable=False, default="")
    agent_url = Column(String(256), nullable=False, default="")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_agent_jobs_note_status", "note_id", "status"),
    )
