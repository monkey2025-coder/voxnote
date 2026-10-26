from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# JWT 密钥,生产环境必须通过环境变量覆盖
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'db' / 'app.db'}"

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR") or (BASE_DIR / "uploads"))
AUDIO_DIR = UPLOAD_DIR / "audio"
IMAGE_DIR = UPLOAD_DIR / "images"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ---------- Agent 编排 ----------

ZY_WEB_BASE_URL = (os.environ.get("ZY_WEB_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
ZY_WEB_ACCESS_KEY = (os.environ.get("ZY_WEB_ACCESS_KEY") or "").strip()
ZY_AGENT_ID = (os.environ.get("ZY_AGENT_ID") or "app_launcher").strip()

SANDBOX_PUBLIC_HOST = (os.environ.get("SANDBOX_PUBLIC_HOST") or "").strip()
SANDBOX_PUBLIC_SCHEME = (os.environ.get("SANDBOX_PUBLIC_SCHEME") or "http").strip() or "http"
SANDBOX_CONTAINERS = (os.environ.get("SANDBOX_CONTAINERS") or "zy-sandbox-1,zy-sandbox-2,zy-sandbox-3,zy-sandbox-4").strip()
SANDBOX_PORTS = (os.environ.get("SANDBOX_PORTS") or "8000,8001,8002").strip()
SANDBOX_HOST_PORT_BASE = _env_int("SANDBOX_HOST_PORT_BASE", 18000)

AGENT_WAIT_TEXT_TIMEOUT = _env_float("AGENT_WAIT_TEXT_TIMEOUT", 180.0)
AGENT_RUN_TIMEOUT = _env_float("AGENT_RUN_TIMEOUT", 1800.0)
