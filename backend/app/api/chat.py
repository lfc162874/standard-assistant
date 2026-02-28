"""聊天接口：提供非流式与流式问答接口。"""

from datetime import datetime, timezone
import json
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.model_service import UnsupportedModelError
from app.services.qa_service import ask_standard_assistant, stream_standard_assistant

router = APIRouter()


class ChatRequest(BaseModel):
    """聊天请求体。"""

    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    model_id: str | None = None


class Citation(BaseModel):
    """引用信息（与前端显示字段保持一致）。"""

    standard_code: str
    version: str
    clause: str
    scope: str


class ChatResponse(BaseModel):
    """聊天响应体。"""

    answer: str
    citations: list[Citation]
    data: dict
    action: Literal["continue", "clarify"]
    trace_id: str
    timestamp: str


def _sse(data: dict) -> str:
    """将对象编码为 SSE data 块。"""

    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """非流式问答接口。"""

    trace_id = str(uuid4())
    memory_session_key = f"{payload.user_id}:{payload.session_id}"
    try:
        # 服务层统一完成：向量检索 + Prompt 组装 + LLM 生成。
        qa_result = ask_standard_assistant(
            payload.query,
            memory_session_key,
            payload.model_id,
        )
    except UnsupportedModelError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"模型选择错误: {exc}",
        ) from exc
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
        answer=qa_result.answer,
        citations=[
            Citation(
                standard_code=item.standard_code,
                version=item.version,
                clause=item.clause,
                scope=item.scope,
            )
            for item in qa_result.citations
        ],
        data={
            "intent": "clause_qa",
            "session_id": payload.session_id,
            "user_id": payload.user_id,
            "provider": f"{qa_result.provider}+chroma",
            "retrieved_count": qa_result.retrieved_count,
            "model_id": qa_result.model_id,
            "model_name": qa_result.model_name,
        },
        action=qa_result.action,
        trace_id=trace_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest) -> StreamingResponse:
    """流式问答接口（SSE）。"""

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
                "requested_model_id": payload.model_id,
            }
        )

        answer_parts: list[str] = []
        stream_result = None
        try:
            stream_result = stream_standard_assistant(
                payload.query,
                memory_session_key,
                payload.model_id,
            )
            for delta in stream_result.chunks:
                answer_parts.append(delta)
                yield _sse(
                    {
                        "type": "delta",
                        "content": delta,
                    }
                )
        except UnsupportedModelError as exc:
            yield _sse(
                {
                    "type": "error",
                    "status": 400,
                    "error": f"模型选择错误: {exc}",
                    "trace_id": trace_id,
                }
            )
            return
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
        if stream_result is None:
            yield _sse(
                {
                    "type": "error",
                    "status": 500,
                    "error": "流式结果为空",
                    "trace_id": trace_id,
                }
            )
            return

        # 结束包提供与非流式接口一致的关键字段，便于前端统一渲染。
        yield _sse(
                {
                    "type": "done",
                    "answer": answer,
                    "citations": [
                        {
                            "standard_code": item.standard_code,
                            "version": item.version,
                            "clause": item.clause,
                            "scope": item.scope,
                        }
                        for item in stream_result.citations
                    ],
                    "data": {
                        "intent": "clause_qa",
                        "session_id": payload.session_id,
                        "user_id": payload.user_id,
                        "provider": f"{stream_result.provider}+chroma",
                        "retrieved_count": stream_result.retrieved_count,
                        "model_id": stream_result.model_id,
                        "model_name": stream_result.model_name,
                    },
                    "action": stream_result.action,
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
