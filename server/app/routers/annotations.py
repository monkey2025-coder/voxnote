import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Note, Annotation
from app.schemas import AnnotationResponse
from app.dependencies.auth import get_current_user
from app.core.config import IMAGE_DIR

router = APIRouter(tags=["批注"])

ALLOWED_IMAGE_SUFFIX = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def annotation_to_response(a: Annotation) -> AnnotationResponse:
    return AnnotationResponse(
        id=a.id,
        note_id=a.note_id,
        type=a.type,
        content=f"/files/images/{a.content}" if a.type == "image" else a.content,
        created_at=a.created_at,
    )


@router.post("/notes/{note_id}/annotations", response_model=AnnotationResponse,
             status_code=status.HTTP_201_CREATED, summary="添加批注(文字传 content,图片传 file)")
async def create_annotation(
    note_id: int,
    type: str = Form(...),
    content: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.get(Note, note_id)
    if note is None or note.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")

    if type == "text":
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文字批注需要 content")
        stored_content = content
    elif type == "image":
        if file is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片批注需要上传 file")
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_IMAGE_SUFFIX:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的图片格式 {suffix}")
        stored_content = f"{current_user.id}/{uuid.uuid4().hex}{suffix}"
        abs_path = IMAGE_DIR / stored_content
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(await file.read())
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type 只能是 text 或 image")

    annotation = Annotation(user_id=current_user.id, note_id=note_id, type=type, content=stored_content)
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation_to_response(annotation)


@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除批注")
def delete_annotation(annotation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    annotation = db.get(Annotation, annotation_id)
    if annotation is None or annotation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批注不存在")
    if annotation.type == "image":
        img = IMAGE_DIR / annotation.content
        if img.exists():
            img.unlink()
    db.delete(annotation)
    db.commit()
