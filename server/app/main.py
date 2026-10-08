from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.core.config import BASE_DIR, AUDIO_DIR, IMAGE_DIR
from app.routers import auth, projects, notes, annotations, sync, files

# 建表与上传目录
Base.metadata.create_all(bind=engine)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="语音记事本 Server", version="0.1.0")

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(notes.router)
app.include_router(annotations.router)
app.include_router(sync.router)
app.include_router(files.router)  # 文件下载带认证,替代之前的公开静态挂载


# ---------- Web 前端托管(生产模式:由 FastAPI 直接提供 web/dist) ----------
WEB_DIST = BASE_DIR / "web_dist"

if WEB_DIST.exists():
    # 静态资源(js/css/图标)
    assets = WEB_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        """SPA 回退:文件存在则返回文件,否则返回 index.html 交给前端路由。

        注册在最后,不影响上面的 API 路由(FastAPI 按注册顺序匹配)。
        """
        if full_path:
            candidate = (WEB_DIST / full_path).resolve()
            # 防路径穿越
            if candidate.is_file() and str(candidate).startswith(str(WEB_DIST.resolve())):
                return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
else:
    @app.get("/", summary="健康检查")
    def root():
        return {"status": "ok", "service": "voice-notes-server", "web": "not built"}
