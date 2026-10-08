# VoxNote 语音记事本

说话即记录。手机 App 录音，服务端自动转写成文字，网页端整理归档到项目。

## 功能

- 📱 **Android App** — 一键录音，自动上传，离线自动补传
- 🤖 **语音转文字** — 服务端 Whisper 模型自动转写，支持中英文
- 🗂️ **网页整理** — 拖拽或下拉把语音归入项目，添加文字/图片批注
- 🔐 **多用户隔离** — 每个用户只能看到自己的数据

## 项目结构

```
├── android/   Android App (Kotlin + Jetpack Compose)
├── web/       网页管理端 (Vue 3 + Element Plus)
└── server/    后端服务 (Python FastAPI + SQLite + faster-whisper)
```

## 快速开始

### 服务端

```bash
cd server
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

或用 Docker（自动预下载 Whisper 模型）：

```bash
docker build -t voxnote ./server
docker run -p 8000:8000 voxnote
```

### 网页端

```bash
cd web
npm install
npm run dev
```

### Android App

首次使用：登录页点右上角齿轮 → 填服务器地址（如 `http://192.168.1.10:8000`）→ 保存。

## 使用流程

1. App 录音 → 上传（自动进"未整理"池，服务端同步转写文字）
2. 网页端打开整理页 → 把语音拖进项目
3. 项目详情页可编辑文字、添加批注、排序

## 环境变量

| 变量              | 默认      | 说明                                  |
| ----------------- | --------- | ------------------------------------- |
| `WHISPER_MODEL` | `small` | 转写模型，可选 tiny/base/small/medium |
| `WHISPER_CACHE` | -         | 模型缓存目录                          |
