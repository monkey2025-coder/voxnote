"""调用 zy-web Agent 的 SSE 客户端。

zy-web 的 /run 在客户端断开时会取消任务，因此必须把 SSE 读到 done。
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.core.config import ZY_AGENT_ID, ZY_WEB_ACCESS_KEY, ZY_WEB_BASE_URL


class AgentClientError(RuntimeError):
    """Agent 调用失败。"""


def run_agent(
    prompt: str,
    session_id: str,
    sandbox_override: dict[str, Any],
    timeout_seconds: float = 1800.0,
) -> dict[str, Any]:
    """执行一次 Agent，返回 {run_id, answer, usage, model, duration_ms}。

    任何失败都抛 AgentClientError；调用方负责把错误写入 AgentJob。
    """
    url = f"{ZY_WEB_BASE_URL}/api/agents/{ZY_AGENT_ID}/run"
    headers = {"Content-Type": "application/json"}
    if ZY_WEB_ACCESS_KEY:
        headers["X-Access-Key"] = ZY_WEB_ACCESS_KEY
    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "sandbox_override": sandbox_override,
    }

    read_timeout = max(float(timeout_seconds or 0), 1.0)
    deadline = time.monotonic() + read_timeout
    errors: list[str] = []
    done: dict[str, Any] | None = None

    try:
        with httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=read_timeout, write=30.0, pool=10.0)
        ) as client:
            with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    body = response.read().decode("utf-8", "replace")
                    raise AgentClientError(
                        f"zy-web 返回 {response.status_code}: {body[:500]}"
                    )

                for line in response.iter_lines():
                    if time.monotonic() > deadline:
                        raise AgentClientError("Agent 运行超时")
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue

                    raw = line[5:].strip()
                    if not raw:
                        continue
                    try:
                        item = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    event = item.get("event")
                    data = item.get("data")
                    if event == "error":
                        errors.append(str(data))
                    elif event == "done":
                        if isinstance(data, dict):
                            done = data
                        break
    except AgentClientError:
        raise
    except httpx.HTTPError as exc:
        raise AgentClientError(f"连接 zy-web 失败：{type(exc).__name__}: {exc}") from exc

    if done is None:
        detail = errors[-1] if errors else "未收到 done 事件"
        raise AgentClientError(f"Agent 未正常结束：{detail}")

    status = done.get("status")
    if status != "completed":
        detail = done.get("error") or (errors[-1] if errors else f"运行状态 {status}")
        raise AgentClientError(str(detail))

    return {
        "run_id": done.get("run_id") or "",
        "answer": done.get("answer"),
        "usage": done.get("usage"),
        "model": done.get("model"),
        "duration_ms": done.get("duration_ms"),
    }
