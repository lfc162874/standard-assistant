# 标准智能助手 (Standard Assistant)

面向“标准信息查询”场景的 Web 单页智能问答系统。  
当前版本已完成基础检索增强 RAG 链路：

- PostgreSQL 标准元信息向量化入库（Chroma）
- 问答时先检索再生成（RAG）
- `citations` 返回引用信息（含标准号、发布日期、标准名称、适用范围）
- SSE 流式输出 + Markdown 渲染
- Redis 会话记忆（Memory）
- 多模型切换（`deepseek-chat` / `deepseek-reasoner` / `qwen-plus`）
- 前端工作台布局（左侧对话 + 右侧引用信息面板）

## 当前能力

- 前后端分离：`frontend/` + `backend/`
- 后端：FastAPI + LangChain（支持 DeepSeek / Qwen）
- 向量检索：Chroma（本地持久化）
- 向量化脚本：`backend/scripts/ingest_standards_meta_to_chroma.py`
- 向量验证脚本：`backend/scripts/test_chroma_vectors.py`
- RAG 评测脚本：`backend/scripts/evaluate_rag.py`
- 前端交互：SSE 流式展示、Markdown 渲染、`Enter` 发送 / `Shift+Enter` 换行
- 接口：
  - `GET /api/v1/health`
  - `GET /api/v1/models`
  - `POST /api/v1/chat`
  - `POST /api/v1/chat/stream`

## 技术栈

- 前端：React 18 + TypeScript + Vite
- 后端：FastAPI + LangChain + LangChain OpenAI Compatible
- 模型：DeepSeek / Qwen（聊天）+ `text-embedding-v4`（向量）
- 数据：PostgreSQL
- 向量库：Chroma
- 会话记忆：Redis

## 项目结构

```text
.
├── frontend/                          # Web 前端（单页聊天）
├── backend/                           # FastAPI 后端
│   ├── app/
│   │   ├── api/                       # /chat /chat/stream /health
│   │   ├── services/                  # qa_service / retrieval_service / redis_history
│   │   └── core/                      # settings
│   └── scripts/
│       ├── ingest_standards_meta_to_chroma.py
│       ├── test_chroma_vectors.py
│       └── evaluate_rag.py
├── docs/                              # 需求、方案、执行计划文档
│   └── eval_questions_template.csv    # RAG 评测样本模板
├── docker-compose.yml
└── README.md
```

## 快速开始（本地开发）

### 1. 启动后端

```bash
cd "/Users/lfc/Documents/New project/backend"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，至少配置：
# DEEPSEEK_API_KEY
# EMBEDDING_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 启动前端

```bash
cd "/Users/lfc/Documents/New project/frontend"
npm install
npm run dev
```

访问地址：

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/api/v1/health`

## RAG 数据准备（必须）

向量化脚本会读取 `drms_standard_middle_sync`，将元信息写入 Chroma。

```bash
cd "/Users/lfc/Documents/New project/backend"
# 首次建议先导入 10000 条做验证
python scripts/ingest_standards_meta_to_chroma.py --truncate --count 10000
```

当前向量文本字段包含：

- `a100` 标准号
- `a298` 标准名称
- `a101` 发布日期
- `a205` 实施日期
- `a206` 作废日期
- `a000` / `a200` 标准状态
- `a825cn` 中国标准分类（中文）
- `a826cn` 国际标准分类（中文）
- `a330` 适用范围

## 向量检索验证

```bash
cd "/Users/lfc/Documents/New project/backend"
python scripts/test_chroma_vectors.py --query "GB 2626 的适用范围是什么？" --top-k 5
```

验证重点：

- `Vector count` 是否大于 0
- TopK 是否命中相关标准
- 输出中是否包含 `a330`

## Step 10.5 回归评测

1. 基于模板准备评测样本：

```bash
cp "/Users/lfc/Documents/New project/docs/eval_questions_template.csv" \
   "/Users/lfc/Documents/New project/docs/eval_questions_v1.csv"
```

2. 运行自动评测：

```bash
cd "/Users/lfc/Documents/New project/backend"
python scripts/evaluate_rag.py \
  --input ../docs/eval_questions_v1.csv \
  --base-url http://127.0.0.1:8000 \
  --output-dir ./eval_reports
```

3. 查看评测输出：

- `rag_eval_report_*.md`：汇总指标与失败样例
- `rag_eval_report_*.json`：完整结构化结果
- `rag_eval_detail_*.csv`：逐条明细（命中/时延/错误）

## API 调用示例

### 非流式

```bash
curl -s http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "session_id": "demo_session",
    "model_id": "deepseek-chat",
    "query": "GB 2626 的适用范围是什么？"
  }'
```

### 流式（SSE）

```bash
curl -N http://127.0.0.1:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "session_id": "demo_session",
    "query": "食品安全相关标准有哪些？"
  }'
```

`citations` 当前字段说明：

- `standard_code`：标准号（来源 `a100`）
- `version`：发布日期（来源 `a101`）
- `clause`：标准名称（来源 `a298`）
- `scope`：适用范围（来源 `a330`）

多模型切换相关字段：

- `GET /api/v1/models`：返回可选模型与默认模型
- 请求体 `model_id`：指定本次问答使用的模型
- 响应 `data.model_id` / `data.model_name`：返回实际生效模型
- 当前已接入模型：`deepseek-chat`、`deepseek-reasoner`、`qwen-plus`

## 关键环境变量（后端）

请参考 `backend/.env.example`，重点如下：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL`
- `DEEPSEEK_BASE_URL`
- `QWEN_API_KEY`
- `QWEN_MODEL`
- `QWEN_BASE_URL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_MODEL`
- `EMBEDDING_BASE_URL`
- `CHROMA_PERSIST_DIR`
- `CHROMA_COLLECTION`
- `RAG_TOP_K`
- `REDIS_URL`
- `MEMORY_TTL_SECONDS`
- `MEMORY_MAX_MESSAGES`

## 文档

- 执行跟踪：`docs/标准智能助手当前执行开发计划（逐步明细）.md`
- RAG 方案：`docs/标准知识检索RAG接入方案与资料清单.md`
- 需求与技术方案：`docs/标准智能助手需求与技术方案.md`
- 前后端详细计划：`docs/标准智能助手前后端详细开发计划.md`
- GitHub 协作指南：`docs/GitHub提交与协作指南.md`

## 开源协议

本项目采用 [MIT License](./LICENSE)。

## 安全提示

- 不要提交真实密钥（`.env` 不应入库）。
- 若密钥泄露，请立即在供应商控制台轮换。
