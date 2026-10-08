# =================== Stage 1: 构建 Web 前端 ===================
FROM node:22-alpine AS web-builder
# npm 国内镜像,加速依赖下载
RUN npm config set registry https://registry.npmmirror.com
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY server/requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

ARG WHISPER_MODEL=small
ENV WHISPER_MODEL=${WHISPER_MODEL} \
    WHISPER_CACHE=/code/models \
    HF_ENDPOINT=https://hf-mirror.com
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8', download_root='/code/models')"

COPY server/app ./app

COPY --from=web-builder /web/dist ./web_dist

VOLUME ["/code/db", "/code/uploads", "/code/models"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
