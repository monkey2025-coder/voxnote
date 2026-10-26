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

# Debian 镜像源可能因网络问题不可达：按顺序尝试多个镜像，任一成功即可。
# 如果完全不需要 ffmpeg CLI，可在 build args 里设置 INSTALL_FFMPEG=false
# （faster-whisper 的 PyAV 自带解码库，通常仍可转写）。
ARG INSTALL_FFMPEG=true
ARG APT_MIRROR=mirrors.tuna.tsinghua.edu.cn

RUN set -eux; \
    if [ "$INSTALL_FFMPEG" = "true" ]; then \
        cp /etc/apt/sources.list.d/debian.sources /tmp/debian.sources.orig; \
        ok=0; \
        for mirror in "$APT_MIRROR" mirrors.ustc.edu.cn mirrors.cloud.tencent.com mirrors.aliyun.com deb.debian.org; do \
            cp /tmp/debian.sources.orig /etc/apt/sources.list.d/debian.sources; \
            sed -i -E "s|https?://[^/]+/debian|http://${mirror}/debian|g" /etc/apt/sources.list.d/debian.sources; \
            if apt-get -o Acquire::Retries=1 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 update; then \
                if apt-get install -y --no-install-recommends ffmpeg; then ok=1; break; fi; \
            fi; \
        done; \
        rm -f /tmp/debian.sources.orig; \
        rm -rf /var/lib/apt/lists/*; \
        [ "$ok" = "1" ]; \
    fi

WORKDIR /code

COPY server/requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

ARG WHISPER_MODEL=small
ENV WHISPER_MODEL=${WHISPER_MODEL} \
    WHISPER_CACHE=/code/models \
    # HuggingFace 国内镜像,加速模型下载
    HF_ENDPOINT=https://hf-mirror.com \
    # 单次下载超时(秒),避免网络慢时过早失败
    HF_HUB_DOWNLOAD_TIMEOUT=120 \
    # 禁用 Xet 协议(它会绕过镜像直连官方服务器导致 401),强制走普通 HTTP
    HF_HUB_DISABLE_XET=1
# 预下载模型可以加快首次转写；如果构建时网络不稳定，失败也不阻断镜像构建，
# 运行时会再次尝试下载并缓存到 /code/models 卷。
RUN for i in 1 2; do \
        python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8', download_root='/code/models')" && break; \
        echo "Whisper 模型预下载第 ${i} 次失败，稍后重试"; \
        sleep 5; \
    done || echo "Whisper 模型预下载失败，将在首次转写时重新下载"

COPY server/app ./app

COPY --from=web-builder /web/dist ./web_dist

VOLUME ["/code/db", "/code/uploads", "/code/models"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
