from fastapi import FastAPI

from app.database import Base, engine
from app.core.config import AUDIO_DIR, IMAGE_DIR
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


@app.get("/", summary="健康检查")
def root():
    return {"status": "ok", "service": "voice-notes-server"}
