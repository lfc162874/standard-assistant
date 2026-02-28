# Backend

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，至少填写 DEEPSEEK_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /api/v1/health`
- `GET /api/v1/models` (可切换模型列表)
- `POST /api/v1/chat`
- `POST /api/v1/chat/stream` (SSE 流式输出)

## RAG QA Chain (Enabled)

当前问答链路已接入：
- Chroma 向量检索（元信息）
- LangChain Memory（Redis）
- DeepSeek 生成回答
- `citations` 返回检索命中的标准信息

关键配置：
- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_MODEL`
- `CHROMA_PERSIST_DIR`
- `CHROMA_COLLECTION`
- `RAG_TOP_K`
- `QWEN_API_KEY`
- `QWEN_MODEL`
- `QWEN_BASE_URL`
- `DEFAULT_CHAT_MODEL_ID`
- `CHAT_ENABLED_MODELS`

快速验证（非流式）：

```bash
curl -s http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "session_id": "demo_session",
    "model_id": "deepseek-chat",
    "query": "GB 2626 的发布日期是什么？"
  }'
```

重点看返回字段：
- `answer`：大模型回答
- `citations`：检索命中的标准引用（不应长期为空）
- `data.retrieved_count`：本次检索命中条数
- `data.model_id` / `data.model_name`：本次实际生效模型

可选模型示例：
- `deepseek-chat`
- `deepseek-reasoner`
- `qwen-plus`

## Memory behavior

- Chat memory is enabled via LangChain `RunnableWithMessageHistory`.
- Memory backend is Redis (not local in-process memory).
- Memory key uses `user_id + session_id` with prefix `MEMORY_KEY_PREFIX`.
- Reusing the same `session_id` preserves context; creating a new `session_id` starts a new conversation.
- Session history expires by `MEMORY_TTL_SECONDS`, and list length is capped by `MEMORY_MAX_MESSAGES`.

## Metadata Vector Ingest (PostgreSQL -> Chroma)

脚本位置：`scripts/ingest_standards_meta_to_chroma.py`

1) 在 `.env` 中配置：
- `PG_HOST=localhost`
- `PG_PORT=5432`
- `PG_USER=postgres`
- `PG_PASSWORD=123456`
- `PG_DATABASE=postgres`（按你的实际库名改）
- `PG_SCHEMA=public`
- `PG_TABLE=drms_standard_middle_sync`
- `EMBEDDING_API_KEY=<你的线上 embedding key>`
- `EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`
- `EMBEDDING_MODEL=text-embedding-v4`
- `CHROMA_PERSIST_DIR=./chroma_data`
- `CHROMA_COLLECTION=standards_meta_v1`

2) 首次全量入库（清空并重建集合）：

```bash
python scripts/ingest_standards_meta_to_chroma.py --truncate
```

3) 指定测试数据量（例如先导入 10000 条）：

```bash
python scripts/ingest_standards_meta_to_chroma.py --truncate --count 10000
```

说明：
- 该脚本不依赖 `is_deleted` 字段。
- 该脚本不依赖 `update_time` 字段。
- 当前写入向量的元信息文本包含：`a100/a298/a101/a205/a206/a000/a200/a825cn/a826cn/a330`。
- 向量 ID 规则：`<table>:<id>`，重复执行会做 upsert（覆盖同 ID）。

常见报错排查：
- 如果出现 `InvalidParameter: input.contents`，通常是 embedding 服务不接受非字符串或 token-array 输入。
- 当前脚本已内置兼容策略：优先批量请求，失败后自动降级为逐条字符串请求。

## How To Test Vector Data

### 1) Verify count after ingest

```bash
python scripts/test_chroma_vectors.py --query "口罩相关标准有哪些？" --top-k 5
```

输出里会看到：
- `Vector count`：集合内总向量条数
- TopK 命中项：`id / distance / a100 / a298 / a101 / a825cn / a826cn / a330`

### 2) Recommended test questions

```bash
python scripts/test_chroma_vectors.py --query "GB 2626 的发布日期是什么？" --top-k 5
python scripts/test_chroma_vectors.py --query "食品安全相关国家标准有哪些？" --top-k 5
python scripts/test_chroma_vectors.py --query "国际标准分类里和电气有关的标准有哪些？" --top-k 5
```

### 3) What counts as a pass (quick check)
- 结果中应出现语义相关标准，且 `a100/a298` 可读。
- `distance` 越小通常越相关（同一模型与同一集合内可横向比较）。
- 若命中明显不相关，先检查：
  - 向量文本模板是否缺少关键信息
  - 输入数据是否包含空值/脏值
  - 集合是否导入了正确数据（`--truncate` 后重跑）

## Step 10.5 评测与调优

### 1) 准备评测样本

使用模板：

```bash
cp ../docs/eval_questions_template.csv ../docs/eval_questions_v1.csv
```

按需编辑 `eval_questions_v1.csv`，核心字段：
- `query`：问题
- `expected_standard_codes`：期望标准号（多个用 `|` 分隔）
- `expected_keywords`：期望关键词（多个用 `|` 分隔）

### 2) 运行自动评测

```bash
python scripts/evaluate_rag.py \
  --input ../docs/eval_questions_v1.csv \
  --base-url http://127.0.0.1:8000 \
  --output-dir ./eval_reports
```

### 3) 输出结果

脚本会输出三份文件：
- `rag_eval_report_*.json`：完整结果（含每条样本）
- `rag_eval_report_*.md`：汇总报告
- `rag_eval_detail_*.csv`：逐条明细，便于错例复盘

### 4) 重点指标解释

- `top1_hit_rate`：期望标准号是否命中第一条 citation
- `topk_hit_rate`：期望标准号是否命中 citations 列表任一项
- `citation_coverage_rate`：回答含 citation 的比例
- `clarify_rate`：返回 `action=clarify` 的比例
- `p95_latency_ms`：95 分位时延
