from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Project
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["项目"])


def to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
        updated_at=project.updated_at,
        note_count=len(project.notes),
    )


@router.get("", response_model=list[ProjectResponse], summary="项目列表")
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()
    return [to_response(p) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="新建项目")
def create_project(req: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = Project(user_id=current_user.id, name=req.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return to_response(project)


def get_owned_project(project_id: int, db: Session, current_user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


@router.put("/{project_id}", response_model=ProjectResponse, summary="重命名项目")
def update_project(project_id: int, req: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_owned_project(project_id, db, current_user)
    project.name = req.name
    db.commit()
    db.refresh(project)
    return to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除项目(含其下所有记录)")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_owned_project(project_id, db, current_user)
    db.delete(project)
    db.commit()
