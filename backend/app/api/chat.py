from datetime import datetime, timezone
import json
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.qa_service import ask_standard_assistant, stream_standard_assistant

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)


class Citation(BaseModel):
    standard_code: str
    version: str
    clause: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    data: dict
    action: Literal["continue", "clarify"]
    trace_id: str
    timestamp: str


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    trace_id = str(uuid4())
    memory_session_key = f"{payload.user_id}:{payload.session_id}"
    try:
        # 统一由服务层处理 LangChain + DeepSeek 调用。
        answer = ask_standard_assistant(payload.query, memory_session_key)
    except ValueError as exc:
        # 配置类错误（例如缺少 API Key）直接返回 500，便于联调快速定位。
        raise HTTPException(
            status_code=500,
            detail=f"模型配置错误: {exc}",
        ) from exc
    except Exception as exc:
        # 远端模型调用失败使用 502，表示上游服务异常。
        raise HTTPException(
            status_code=502,
            detail=f"模型调用失败: {exc}",
        ) from exc

    return ChatResponse(
        answer=answer,
        citations=[],
        data={
            "intent": "clause_qa",
            "session_id": payload.session_id,
            "user_id": payload.user_id,
            "provider": "deepseek",
        },
        action="continue",
        trace_id=trace_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest) -> StreamingResponse:
    trace_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    memory_session_key = f"{payload.user_id}:{payload.session_id}"

    def generate():
        # 首包先给元信息，前端可用于追踪当前请求。
        yield _sse(
            {
                "type": "meta",
                "trace_id": trace_id,
                "timestamp": timestamp,
            }
        )

        answer_parts: list[str] = []
        try:
            for delta in stream_standard_assistant(payload.query, memory_session_key):
                answer_parts.append(delta)
                yield _sse(
                    {
                        "type": "delta",
                        "content": delta,
                    }
                )
        except ValueError as exc:
            yield _sse(
                {
                    "type": "error",
                    "status": 500,
                    "error": f"模型配置错误: {exc}",
                    "trace_id": trace_id,
                }
            )
            return
        except Exception as exc:
            yield _sse(
                {
                    "type": "error",
                    "status": 502,
                    "error": f"模型调用失败: {exc}",
                    "trace_id": trace_id,
                }
            )
            return

        answer = "".join(answer_parts).strip()
        if not answer:
            answer = "没有生成有效回答，请重试。"

        # 结束包提供与非流式接口一致的关键字段，便于前端统一渲染。
        yield _sse(
            {
                "type": "done",
                "answer": answer,
                "citations": [],
                "data": {
                    "intent": "clause_qa",
                    "session_id": payload.session_id,
                    "user_id": payload.user_id,
                    "provider": "deepseek",
                },
                "action": "continue",
                "trace_id": trace_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
