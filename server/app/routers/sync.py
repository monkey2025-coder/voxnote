from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Project, Note, Annotation
from app.dependencies.auth import get_current_user
from app.routers.notes import note_to_detail
from app.routers.projects import to_response as project_to_response
from app.routers.annotations import annotation_to_response

router = APIRouter(tags=["同步"])


@router.get("/sync", summary="增量同步:拉取 since 之后变更的所有数据(不传则全量,用于新设备)")
def sync(
    since: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = since or datetime.min

    projects = db.query(Project).filter(Project.user_id == current_user.id, Project.updated_at > since).all()
    notes = db.query(Note).filter(Note.user_id == current_user.id, Note.updated_at > since).all()
    annotations = (
        db.query(Annotation)
        .filter(Annotation.user_id == current_user.id, Annotation.created_at > since)
        .all()
    )

    return {
        "server_time": datetime.utcnow(),
        "projects": [project_to_response(p) for p in projects],
        "notes": [note_to_detail(n) for n in notes],
        "annotations": [annotation_to_response(a) for a in annotations],
    }
