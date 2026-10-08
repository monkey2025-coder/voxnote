from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.core.config import UPLOAD_DIR, AUDIO_DIR, IMAGE_DIR
from app.routers import auth, projects, notes, annotations, sync

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

# 静态文件:音频与批注图片
app.mount("/files", StaticFiles(directory=str(UPLOAD_DIR)), name="files")


@app.get("/", summary="健康检查")
def root():
    return {"status": "ok", "service": "voice-notes-server"}
