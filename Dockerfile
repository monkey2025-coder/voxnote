# =================== Stage 1: 构建 Web 前端 ===================
FROM node:22-alpine AS web-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# =================== Stage 2: Python 后端 ===================
FROM python:3.11-slim

# faster-whisper 解码音频需要 ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 预下载 whisper 模型,避免运行时联网(默认 small,可用 --build-arg 覆盖)
ARG WHISPER_MODEL=small
ENV WHISPER_MODEL=${WHISPER_MODEL} \
    WHISPER_CACHE=/code/models
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8', download_root='/code/models')"

# 后端代码
COPY server/app ./app

# 前端构建产物 -> web_dist,由 FastAPI 直接托管
COPY --from=web-builder /web/dist ./web_dist

# 持久化卷:数据库、上传文件、模型缓存
VOLUME ["/code/db", "/code/uploads", "/code/models"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
