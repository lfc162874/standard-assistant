# 标准智能助手 (Standard Assistant)

一个面向标准信息查询场景的 Web 单页智能问答系统。  
当前版本已支持：
- LangChain + DeepSeek 模型问答
- SSE 流式输出
- Markdown 格式回答渲染
- 基于 `user_id + session_id` 的对话记忆（Redis 后端）

## 项目特性
- 前后端分离架构，目录清晰，便于独立开发和部署。
- 后端基于 FastAPI，支持同步与流式两种聊天接口。
- 前端基于 React + Vite，内置会话管理与后端健康检查。
- 记忆链路基于 LangChain `RunnableWithMessageHistory`。
- 提供 Docker Compose 一键启动，降低本地环境门槛。

## 技术栈
- 前端：React 18 + TypeScript + Vite
- 后端：FastAPI + LangChain + DeepSeek(OpenAI-Compatible)
- 数据与缓存：PostgreSQL + Redis
- 部署：Docker Compose

## 目录结构
```text
.
├── frontend/                # Web 前端
├── backend/                 # FastAPI 后端
├── docs/                    # 需求、计划、协作文档
├── docker-compose.yml       # 本地容器编排
└── README.md
```

## 快速开始

### 方式一：Docker（推荐）
```bash
cd "/Users/lfc/Documents/New project"
docker compose up --build
```

启动后访问：
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/api/v1/health`

### 方式二：本地开发

后端：
```bash
cd "/Users/lfc/Documents/New project/backend"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，至少配置 DEEPSEEK_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：
```bash
cd "/Users/lfc/Documents/New project/frontend"
cp .env.example .env
npm install
npm run dev
```

## 环境变量说明（后端）
核心变量见 `backend/.env.example`：
- `DEEPSEEK_API_KEY`：DeepSeek API 密钥
- `DEEPSEEK_MODEL`：默认 `deepseek-chat`
- `DEEPSEEK_BASE_URL`：默认 `https://api.deepseek.com/v1`
- `REDIS_URL`：默认 `redis://localhost:6379/0`
- `MEMORY_KEY_PREFIX`：记忆键前缀
- `MEMORY_TTL_SECONDS`：记忆过期秒数
- `MEMORY_MAX_MESSAGES`：单会话最大消息数

## API 概览
- `GET /api/v1/health`：服务健康检查
- `POST /api/v1/chat`：非流式问答
- `POST /api/v1/chat/stream`：SSE 流式问答

## 开发与文档
- 执行型开发计划：`docs/标准智能助手当前执行开发计划（逐步明细）.md`
- 需求与技术方案：`docs/标准智能助手需求与技术方案.md`
- 前后端细化计划：`docs/标准智能助手前后端详细开发计划.md`
- RAG 接入方案与资料清单：`docs/标准知识检索RAG接入方案与资料清单.md`
- GitHub 提交指南：`docs/GitHub提交与协作指南.md`

## 开源协议
本项目使用 [MIT License](./LICENSE)。

## 贡献说明
欢迎 Issue 和 Pull Request。建议流程：
1. 从 `main` 新建功能分支（例如 `codex/feature-name`）。
2. 完成功能后提交 PR，并附上变更说明与测试结果。
3. 合并前确保不提交敏感信息（如 `.env`）。

## 安全说明
- 请勿将真实 API Key 提交到仓库。
- 如果密钥曾经泄露，请立即在供应商控制台轮换。
