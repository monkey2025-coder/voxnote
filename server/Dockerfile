FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 预下载 whisper 模型(默认 base,可用 --build-arg 覆盖),避免运行时联网下载
ARG WHISPER_MODEL=base
ENV WHISPER_MODEL=${WHISPER_MODEL} \
    WHISPER_CACHE=/code/models
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8', download_root='/code/models')"

COPY app ./app

# 数据库、上传文件、模型缓存挂到卷上即可持久化
VOLUME ["/code/db", "/code/uploads", "/code/models"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
