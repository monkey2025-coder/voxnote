"""Agent 后台执行器：轮询 AgentJob，调用 zy-web 并回写结果。"""
from __future__ import annotations

import logging
import re
import threading
from datetime import datetime

from app.core import agent_client, sandbox_slots
from app.core.config import (
    AGENT_RUN_TIMEOUT,
    AGENT_WAIT_TEXT_TIMEOUT,
    SANDBOX_PUBLIC_HOST,
    SANDBOX_PUBLIC_SCHEME,
)
from app.database import SessionLocal
from app.models import AgentJob, Note, Project, SandboxApp

ACTIVE_JOB_STATUSES = ("waiting_text", "queued", "running")

logger = logging.getLogger(__name__)

_worker_thread: threading.Thread | None = None
_stop_event = threading.Event()
_POLL_SECONDS = 1.5


def start_worker() -> None:
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_loop, name="agent-worker", daemon=True)
    _worker_thread.start()


def stop_worker() -> None:
    _stop_event.set()
    if _worker_thread is not None:
        _worker_thread.join(timeout=5)


def _loop() -> None:
    _recover_running_jobs()
    while not _stop_event.is_set():
        try:
            worked = _tick()
        except Exception:  # noqa: BLE001
            logger.exception("agent worker tick failed")
            worked = False
        if not worked:
            _stop_event.wait(_POLL_SECONDS)


def _recover_running_jobs() -> None:
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        db.query(AgentJob).filter(AgentJob.status == "running").update(
            {
                AgentJob.status: "failed",
                AgentJob.error: "服务重启，任务中断",
                AgentJob.finished_at: now,
                AgentJob.updated_at: now,
            },
            synchronize_session=False,
        )
        db.commit()
    finally:
        db.close()


def _tick() -> bool:
    db = SessionLocal()
    try:
        # 1. 转写完成的 waiting_text 进入 queued；超时的直接失败
        waiting = db.query(AgentJob).filter(AgentJob.status == "waiting_text").all()
        for job in waiting:
            note = db.get(Note, job.note_id)
            if note is None:
                _fail(job, "原始语音记录已删除")
                continue
            text = (note.text or "").strip()
            if text:
                if not (job.instruction or "").strip():
                    job.instruction = text
                job.status = "queued"
            elif _age_seconds(job.created_at) > AGENT_WAIT_TEXT_TIMEOUT:
                _fail(job, "转写超时，请重试")
        db.commit()

        # 2. 取一条 queued 任务并领取
        job = (
            db.query(AgentJob)
            .filter(AgentJob.status == "queued")
            .order_by(AgentJob.id)
            .first()
        )
        if job is None:
            return False

        now = datetime.utcnow()
        updated = (
            db.query(AgentJob)
            .filter(AgentJob.id == job.id, AgentJob.status == "queued")
            .update(
                {
                    AgentJob.status: "running",
                    AgentJob.started_at: now,
                    AgentJob.updated_at: now,
                },
                synchronize_session=False,
            )
        )
        db.commit()
        if not updated:
            return False
        job_id = job.id
    finally:
        db.close()

    _execute(job_id)
    return True


def _execute(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(AgentJob, job_id)
        if job is None or job.status != "running":
            return

        note = db.get(Note, job.note_id)
        if note is None:
            _fail(job, "原始语音记录已删除")
            db.commit()
            return

        if not SANDBOX_PUBLIC_HOST:
            _fail(job, "服务端未配置 SANDBOX_PUBLIC_HOST")
            db.commit()
            return

        app: SandboxApp | None = None
        created = False
        if job.app_id:
            app = db.get(SandboxApp, job.app_id)
            if app is None or app.status != "active":
                _fail(job, "目标应用不存在或已删除")
                db.commit()
                return
        else:
            try:
                app, created = sandbox_slots.allocate_app(
                    db,
                    user_id=job.user_id,
                    project_id=note.project_id,
                    name=job.app_name or _app_name(db, note),
                )
            except sandbox_slots.NoFreeSlot as exc:
                _fail(job, str(exc))
                db.commit()
                return

        app_url = sandbox_slots.build_app_url(app)
        if not app_url:
            _fail(job, "服务端未配置 SANDBOX_PUBLIC_HOST")
            db.commit()
            return

        now = datetime.utcnow()
        job.app_id = app.id
        job.session_id = app.session_id
        job.app_url = app_url
        job.updated_at = now
        app.last_job_id = job.id
        app.updated_at = now
        db.commit()

        instruction = (job.instruction or note.text or "").strip()
        if not instruction:
            _fail(job, "没有可执行的需求文本")
            db.commit()
            return

        public_base = SANDBOX_PUBLIC_HOST
        if "://" not in public_base:
            public_base = f"{SANDBOX_PUBLIC_SCHEME}://{public_base}"

        override = {
            "containers": app.container,
            "default_port": app.container_port,
            "default_workdir": app.workdir,
            "public_host": public_base,
            "pinned": True,
        }
        prompt = _build_prompt(app, instruction, existing=not created, app_url=app_url)

        try:
            result = agent_client.run_agent(
                prompt,
                app.session_id,
                override,
                timeout_seconds=AGENT_RUN_TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001
            _fail(job, f"{type(exc).__name__}: {exc}")
            db.commit()
            return

        answer = result.get("answer") or ""
        agent_url = _extract_app_url(answer)
        if not agent_url:
            _fail(job, "Agent 未返回应用地址")
            db.commit()
            return

        job.status = "succeeded"
        job.answer = answer
        job.run_id = result.get("run_id") or ""
        job.agent_url = agent_url
        job.error = None
        job.finished_at = datetime.utcnow()
        job.updated_at = job.finished_at
        app.last_job_id = job.id
        app.updated_at = job.finished_at
        db.commit()
    finally:
        db.close()


def _app_name(db, note: Note) -> str:
    if note.project_id:
        project = db.get(Project, note.project_id)
        if project is not None and project.name:
            return project.name
    text = (note.text or "").strip().replace("\n", " ")
    return (text[:30] or "app").strip()


def _build_prompt(app: SandboxApp, instruction: str, *, existing: bool, app_url: str) -> str:
    update_rule = (
        "这是对现有应用的修改：先读取 workdir 下的现有文件，在保留数据和已有功能的基础上修改，不要从零重写。"
        if existing
        else "这是一个新应用：直接在当前 workdir 下创建应用。"
    )
    return f"""【应用信息】
app_id: {app.id}
name: {app.name}
workdir: {app.workdir}
port: {app.container_port}
existing: {"true" if existing else "false"}
public_url: {app_url}

【用户需求】
{instruction}

【执行要求】
1. 只通过 sandbox 工具执行，不要反问用户。
2. 工作目录固定为 {app.workdir}，监听端口固定为 {app.container_port}，必须监听 0.0.0.0。
3. {update_rule}
4. 依赖优先使用镜像中已安装的包；需要额外依赖时再 pip install。
5. 启动应用必须使用 background=True；不要自己拼接访问地址，以工具返回的 url 为准。
6. background=True 时 run_python 的 code 参数就是应用自身的 main.py；禁止在 code 里用 subprocess/nohup/bash 再启动 main.py。前台检查用 background=False，不会覆盖 main.py。
7. 如果用户要求停止旧应用，不要扫描 /proc、ps、ss，也不要手动 kill；直接 background=True 覆盖启动，工具会自动按 app.pid 停止旧进程。
8. 最终回答严格按以下格式输出：
APP_URL: <sandbox 工具返回的 url>
APP_NAME: <应用名>
SUMMARY: <一句话说明做了什么>
"""


def _extract_app_url(answer: str) -> str:
    text = answer or ""
    match = re.search(r"APP_URL:\s*(\S+)", text)
    if match:
        return match.group(1).strip("`'\"<>")
    match = re.search(r"https?://\S+", text)
    return match.group(0) if match else ""


def _fail(job: AgentJob, message: str) -> None:
    now = datetime.utcnow()
    job.status = "failed"
    job.error = message
    job.finished_at = now
    job.updated_at = now


def _age_seconds(value: datetime | None) -> float:
    if value is None:
        return 0.0
    return (datetime.utcnow() - value).total_seconds()
