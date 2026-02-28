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
- `POST /api/v1/chat`
- `POST /api/v1/chat/stream` (SSE 流式输出)

## Memory behavior

- Chat memory is enabled via LangChain `RunnableWithMessageHistory`.
- Memory backend is Redis (not local in-process memory).
- Memory key uses `user_id + session_id` with prefix `MEMORY_KEY_PREFIX`.
- Reusing the same `session_id` preserves context; creating a new `session_id` starts a new conversation.
- Session history expires by `MEMORY_TTL_SECONDS`, and list length is capped by `MEMORY_MAX_MESSAGES`.
