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
| `DATABASE_URL` | `sqlite:///.../db/app.db` | 数据库地址，测试时可指向临时 SQLite |
| `UPLOAD_DIR` | `uploads` | 音频/图片上传目录 |
| `ZY_WEB_BASE_URL` | `http://127.0.0.1:8000` | zy-web 地址（容器内建议用 `http://host.docker.internal:8010`，避免和 voxnote 的 8000 冲突） |
| `ZY_WEB_ACCESS_KEY` | - | zy-web 访问密钥 |
| `ZY_AGENT_ID` | `app_launcher` | 负责上线应用的 Agent id |
| `SANDBOX_PUBLIC_HOST` | - | 沙箱应用对外访问的服务器 IP 或域名 |
| `SANDBOX_PUBLIC_SCHEME` | `http` | 对外访问协议 |
| `SANDBOX_CONTAINERS` | `zy-sandbox-1,...,zy-sandbox-4` | 沙箱容器列表 |
| `SANDBOX_PORTS` | `8000,8001,8002` | 每个容器的应用端口 |
| `SANDBOX_HOST_PORT_BASE` | `18000` | 宿主端口基数 |
| `AGENT_WAIT_TEXT_TIMEOUT` | `180` | 等待转写的秒数 |
| `AGENT_RUN_TIMEOUT` | `1800` | 单次 Agent 运行超时秒数 |

## 语音上线应用（可选）

录音上传后，在安卓端点击「交给 Agent 执行」，voxnote 会把转写文本发给 zy-web 的 `app_launcher` Agent，在固定沙箱槽位里创建或修改应用，并返回可访问 URL。

前置条件：

1. zy-agent 仓库的沙箱容器已启动：`docker compose -f docker/sandbox-compose.yml up -d`。
2. zy-web 在宿主机启动并监听 `0.0.0.0:8010`（配好访问密钥和防火墙），voxnote 容器通过 `host.docker.internal:8010` 访问；不要和 voxnote 共用 8000。
3. voxnote 的 compose 已配置好 `SANDBOX_PUBLIC_HOST` 与防火墙端口 `18001-18204`。
4. zy-agent 的 `data/agents/app_launcher.json` 已配置可用的模型。
