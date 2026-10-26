"""语音记录 → Agent 上线应用的触发与查询接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core import sandbox_slots
from app.core.agent_worker import ACTIVE_JOB_STATUSES
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import AgentJob, Note, SandboxApp, User
from app.schemas import AgentJobResponse, AgentTriggerRequest, SandboxAppResponse

router = APIRouter(tags=["Agent"])


def _get_owned_note(note_id: int, db: Session, user: User) -> Note:
    note = db.get(Note, note_id)
    if note is None or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    return note


def _get_owned_app(app_id: int, db: Session, user: User) -> SandboxApp:
    app = db.get(SandboxApp, app_id)
    if app is None or app.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="应用不存在")
    return app


def _job_response(job: AgentJob, db: Session) -> AgentJobResponse:
    app = db.get(SandboxApp, job.app_id) if job.app_id else None
    app_url = job.app_url or (sandbox_slots.build_app_url(app) if app else "")
    return AgentJobResponse(
        job_id=job.id,
        note_id=job.note_id,
        status=job.status,
        app_id=job.app_id,
        app_name=(app.name if app else (job.app_name or None)),
        app_url=app_url or None,
        answer=job.answer,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def _app_response(app: SandboxApp) -> SandboxAppResponse:
    return SandboxAppResponse(
        id=app.id,
        name=app.name,
        project_id=app.project_id,
        container=app.container,
        container_port=app.container_port,
        host_port=app.host_port,
        url=sandbox_slots.build_app_url(app),
        status=app.status,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


def _active_job_for_app(db: Session, app_id: int) -> AgentJob | None:
    return (
        db.query(AgentJob)
        .filter(
            AgentJob.app_id == app_id,
            AgentJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(AgentJob.id.desc())
        .first()
    )


def _previous_note_app(db: Session, note_id: int, user_id: int) -> SandboxApp | None:
    """同一条语音重试/继续修改时，复用上一次任务创建的应用。"""
    previous = (
        db.query(AgentJob)
        .filter(
            AgentJob.note_id == note_id,
            AgentJob.user_id == user_id,
            AgentJob.app_id.isnot(None),
        )
        .order_by(AgentJob.id.desc())
        .first()
    )
    if previous is None or previous.app_id is None:
        return None
    candidate = db.get(SandboxApp, previous.app_id)
    if (
        candidate is not None
        and candidate.user_id == user_id
        and candidate.status == "active"
    ):
        return candidate
    return None


@router.post(
    "/notes/{note_id}/agent",
    response_model=AgentJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="把语音交给 Agent 执行（等待转写完成后上线应用）",
)
def trigger_agent(
    note_id: int,
    req: AgentTriggerRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(note_id, db, current_user)
    body = req or AgentTriggerRequest()

    # 同一条语音只允许一个进行中的任务，避免安卓重复点击
    existing = (
        db.query(AgentJob)
        .filter(
            AgentJob.note_id == note.id,
            AgentJob.user_id == current_user.id,
            AgentJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(AgentJob.id.desc())
        .first()
    )
    if existing is not None:
        return _job_response(existing, db)

    app: SandboxApp | None = None
    if body.app_id is not None:
        app = _get_owned_app(body.app_id, db, current_user)
        if app.status != "active":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="应用已删除")
    else:
        if note.project_id is not None:
            app = (
                db.query(SandboxApp)
                .filter(
                    SandboxApp.user_id == current_user.id,
                    SandboxApp.project_id == note.project_id,
                    SandboxApp.status == "active",
                )
                .order_by(SandboxApp.id.desc())
                .first()
            )
        if app is None:
            app = _previous_note_app(db, note.id, current_user.id)

    if app is not None and _active_job_for_app(db, app.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该应用已有正在执行的任务")
    if app is None and sandbox_slots.free_slot(db) is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="应用槽位已满")

    instruction = (body.instruction or note.text or "").strip()
    job = AgentJob(
        user_id=current_user.id,
        note_id=note.id,
        app_id=app.id if app else None,
        app_name=(body.app_name or "").strip()[:120],
        status="queued" if instruction else "waiting_text",
        instruction=instruction,
        session_id=app.session_id if app else "",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_response(job, db)


@router.get(
    "/notes/{note_id}/agent",
    response_model=AgentJobResponse,
    summary="查询语音最近一次 Agent 执行状态",
)
def get_note_agent(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(note_id, db, current_user)
    job = (
        db.query(AgentJob)
        .filter(AgentJob.note_id == note.id, AgentJob.user_id == current_user.id)
        .order_by(AgentJob.id.desc())
        .first()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该语音还没有 Agent 任务")
    return _job_response(job, db)


@router.get(
    "/agent-jobs/{job_id}",
    response_model=AgentJobResponse,
    summary="查询单个 Agent 任务",
)
def get_agent_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(AgentJob, job_id)
    if job is None or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return _job_response(job, db)


@router.get("/apps", response_model=list[SandboxAppResponse], summary="我的沙箱应用")
def list_apps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apps = (
        db.query(SandboxApp)
        .filter(SandboxApp.user_id == current_user.id, SandboxApp.status == "active")
        .order_by(SandboxApp.created_at.desc())
        .all()
    )
    return [_app_response(app) for app in apps]


@router.delete("/apps/{app_id}", summary="删除应用并释放槽位（旧进程在槽位复用时停止）")
def delete_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = _get_owned_app(app_id, db, current_user)
    if app.status != "active":
        return {"deleted": False}
    if _active_job_for_app(db, app.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该应用正在执行任务，无法删除")
    app.status = "deleted"
    db.commit()
    return {"deleted": True}
