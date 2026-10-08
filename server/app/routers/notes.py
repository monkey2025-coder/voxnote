import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, Project, Note
from app.schemas import NoteUpdate, NoteResponse, NoteWithAnnotations, AnnotationResponse
from app.dependencies.auth import get_current_user
from app.core.config import AUDIO_DIR

router = APIRouter(tags=["语音记录"])

ALLOWED_AUDIO_SUFFIX = {".m4a", ".aac", ".mp3", ".wav", ".amr", ".ogg"}


def audio_url(note: Note) -> str:
    return f"/files/audio/{note.audio_path}"


def note_to_response(note: Note) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        project_id=note.project_id,
        audio_url=audio_url(note),
        text=note.text,
        duration=note.duration,
        sort_order=note.sort_order,
        recorded_at=note.recorded_at,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def note_to_detail(note: Note) -> NoteWithAnnotations:
    detail = NoteWithAnnotations(**note_to_response(note).model_dump())
    detail.annotations = [
        AnnotationResponse(
            id=a.id, note_id=a.note_id, type=a.type,
            content=f"/files/images/{a.content}" if a.type == "image" else a.content,
            created_at=a.created_at,
        )
        for a in sorted(note.annotations, key=lambda x: x.created_at)
    ]
    return detail


def get_owned_note(note_id: int, db: Session, current_user: User) -> Note:
    note = db.get(Note, note_id)
    if note is None or note.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    return note


def get_owned_project(project_id: int, db: Session, current_user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED, summary="上传语音记录(音频+文字,project_id 可选,不传则进未整理池)")
async def create_note(
    file: UploadFile = File(...),
    project_id: int | None = Form(default=None),
    text: str = Form(default=""),
    duration: float = Form(default=0.0),
    recorded_at: datetime | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if project_id is not None:
        get_owned_project(project_id, db, current_user)

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_AUDIO_SUFFIX:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的音频格式 {suffix}")

    # 存储路径: uploads/audio/<user_id>/<uuid>.m4a
    rel_path = f"{current_user.id}/{uuid.uuid4().hex}{suffix}"
    abs_path = AUDIO_DIR / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(await file.read())

    # 客户端没给文字时,服务端用 whisper 转写;改异步:先存空 text 立即返回,
    # 转写丢到单线程池后台串行跑,完成后回写 note.text(经 updated_at 触发 sync 增量下发)。
    # 这样转写期间不会阻塞事件循环,login 等 IO 请求照常处理。
    need_transcribe = not text.strip()

    max_order = db.query(func.max(Note.sort_order)).filter(
        Note.user_id == current_user.id,
        Note.project_id == project_id,
    ).scalar() or 0
    note = Note(
        user_id=current_user.id,
        project_id=project_id,
        audio_path=rel_path,
        text=text,
        duration=duration,
        sort_order=max_order + 1,
        recorded_at=recorded_at or datetime.utcnow(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    if need_transcribe:
        from app.core.transcribe import submit_transcribe
        submit_transcribe(note.id, abs_path)

    return note_to_response(note)


@router.get("/projects/{project_id}/notes", response_model=list[NoteWithAnnotations], summary="项目下所有记录(含批注)")
def list_notes(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    get_owned_project(project_id, db, current_user)
    notes = (
        db.query(Note)
        .filter(Note.project_id == project_id)
        .order_by(Note.sort_order, Note.recorded_at)
        .all()
    )
    return [note_to_detail(n) for n in notes]


@router.get("/notes/inbox", response_model=list[NoteWithAnnotations], summary="未整理池:所有未归入项目的语音")
def list_inbox(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notes = (
        db.query(Note)
        .filter(Note.user_id == current_user.id, Note.project_id.is_(None))
        .order_by(Note.recorded_at.desc())
        .all()
    )
    return [note_to_detail(n) for n in notes]


@router.put("/notes/{note_id}", response_model=NoteResponse, summary="修改记录(文字/移动项目/排序,project_id 传 null 移回未整理池)")
def update_note(note_id: int, req: NoteUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    note = get_owned_note(note_id, db, current_user)
    fields = req.model_dump(exclude_unset=True)
    if "text" in fields:
        note.text = fields["text"]
    if "sort_order" in fields:
        note.sort_order = fields["sort_order"]
    if "project_id" in fields:
        new_pid = fields["project_id"]
        if new_pid is not None:
            get_owned_project(new_pid, db, current_user)
        note.project_id = new_pid
    db.commit()
    db.refresh(note)
    return note_to_response(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除记录(含音频与批注图片)")
def delete_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    note = get_owned_note(note_id, db, current_user)
    # 清理音频文件
    audio_file = AUDIO_DIR / note.audio_path
    if audio_file.exists():
        audio_file.unlink()
    # 清理批注图片文件
    from app.models import Annotation
    from app.core.config import IMAGE_DIR
    for a in note.annotations:
        if a.type == "image":
            img = IMAGE_DIR / a.content
            if img.exists():
                img.unlink()
    db.delete(note)
    db.commit()
