"""沙箱槽位分配：把应用固定到某个容器的某个端口。"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import (
    SANDBOX_CONTAINERS,
    SANDBOX_HOST_PORT_BASE,
    SANDBOX_PORTS,
    SANDBOX_PUBLIC_HOST,
    SANDBOX_PUBLIC_SCHEME,
)
from app.models import SandboxApp


class NoFreeSlot(RuntimeError):
    """所有沙箱槽位都已被占用。"""


@dataclass(frozen=True)
class SandboxSlot:
    slot_key: str
    container: str
    container_port: int
    host_port: int
    workdir: str


def _parse_slots() -> list[SandboxSlot]:
    containers = [item.strip() for item in SANDBOX_CONTAINERS.split(",") if item.strip()]
    ports: list[int] = []
    for item in SANDBOX_PORTS.split(","):
        try:
            ports.append(int(item.strip()))
        except ValueError:
            continue

    slots: list[SandboxSlot] = []
    for container_index, container in enumerate(containers, 1):
        for port_index, port in enumerate(ports):
            slots.append(
                SandboxSlot(
                    slot_key=f"sb{container_index}-{port}",
                    container=container,
                    container_port=port,
                    host_port=SANDBOX_HOST_PORT_BASE + port_index * 100 + container_index,
                    workdir=f"/workspace/apps/slot-{container_index}-{port_index}",
                )
            )
    return slots


SLOTS = _parse_slots()


def active_slots(db: Session) -> set[tuple[str, int]]:
    rows = (
        db.query(SandboxApp.container, SandboxApp.container_port)
        .filter(SandboxApp.status == "active")
        .all()
    )
    return {(row[0], row[1]) for row in rows}


def free_slot(db: Session) -> SandboxSlot | None:
    occupied = active_slots(db)
    for slot in SLOTS:
        if (slot.container, slot.container_port) not in occupied:
            return slot
    return None


def build_app_url(app: SandboxApp) -> str:
    """按槽位计算对外访问地址；未配置公网主机时返回空字符串。"""
    host = SANDBOX_PUBLIC_HOST.strip()
    if not host:
        return ""
    base = host.rstrip("/")
    if "://" not in base:
        base = f"{SANDBOX_PUBLIC_SCHEME}://{base}"
    return f"{base}:{app.host_port}"


def allocate_app(
    db: Session,
    *,
    user_id: int,
    project_id: int | None,
    name: str,
) -> tuple[SandboxApp, bool]:
    """为项目复用应用，或分配一个新槽位。

    返回 (app, created)。created=True 表示新建，调用方负责 commit。
    """
    if project_id is not None:
        existing = (
            db.query(SandboxApp)
            .filter(
                SandboxApp.user_id == user_id,
                SandboxApp.project_id == project_id,
                SandboxApp.status == "active",
            )
            .order_by(SandboxApp.id.desc())
            .first()
        )
        if existing is not None:
            return existing, False

    slot = free_slot(db)
    if slot is None:
        raise NoFreeSlot("没有空闲的沙箱槽位")

    app = SandboxApp(
        user_id=user_id,
        project_id=project_id,
        name=(name or "app").strip()[:120] or "app",
        slot_key=slot.slot_key,
        container=slot.container,
        container_port=slot.container_port,
        host_port=slot.host_port,
        workdir=slot.workdir,
        session_id="",
        status="active",
    )
    db.add(app)
    db.flush()
    app.session_id = f"voxnote-app-{app.id}"
    return app, True
