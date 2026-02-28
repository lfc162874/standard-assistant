from __future__ import annotations

"""问答服务：负责将检索结果、会话记忆与大模型生成串成完整 RAG 链路。"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator, Literal

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from redis import Redis

from app.core.settings import (
    get_llm_temperature,
    get_llm_timeout_seconds,
    get_memory_key_prefix,
    get_memory_max_messages,
    get_memory_ttl_seconds,
    get_redis_url,
)
from app.services.model_service import resolve_chat_model
from app.services.redis_history import RedisChatMessageHistory
from app.services.retrieval_service import RetrievedStandard, build_retrieval_context, retrieve_standards

SYSTEM_PROMPT = """
你是“标准智能助手”。
请遵循以下规则回答：
1. 优先基于“检索上下文”回答，不要编造不存在的标准信息。
2. 如果检索上下文不足以支撑结论，明确说明信息不足，并提示用户补充标准号或关键词。
3. 回答语言使用中文，表达简洁清晰。
4. 回答中尽量引用标准号与标准名称。
""".strip()


@dataclass
class CitationPayload:
    """接口返回的引用结构（保持与前端现有协议兼容）。"""

    standard_code: str
    version: str
    clause: str
    scope: str


@dataclass
class QAResult:
    """非流式问答结果。"""

    answer: str
    citations: list[CitationPayload]
    action: Literal["continue", "clarify"]
    retrieved_count: int
    model_id: str
    model_name: str
    provider: str


@dataclass
class QAStreamResult:
    """流式问答结果（包含流式分片迭代器与最终引用信息）。"""

    chunks: Iterator[str]
    citations: list[CitationPayload]
    action: Literal["continue", "clarify"]
    retrieved_count: int
    model_id: str
    model_name: str
    provider: str


def _safe_text(value: object) -> str:
    """统一安全转字符串。"""

    if value is None:
        return ""
    return str(value).strip()


def _build_citations(records: list[RetrievedStandard], max_items: int = 5) -> list[CitationPayload]:
    """从检索命中结果构造引用列表。"""

    citations: list[CitationPayload] = []
    seen: set[tuple[str, str, str]] = set()

    for record in records:
        metadata = record.metadata
        standard_code = _safe_text(metadata.get("a100"))
        standard_name = _safe_text(metadata.get("a298"))
        publish_date = _safe_text(metadata.get("a101"))
        scope = _safe_text(metadata.get("a330"))

        if not standard_code and not standard_name:
            continue

        dedup_key = (standard_code, standard_name, publish_date)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        citations.append(
            CitationPayload(
                standard_code=standard_code or "未知标准号",
                # 现阶段沿用原有字段命名 `version`，内容填发布日期，避免前端协议破坏。
                version=publish_date or "发布日期未知",
                # 现阶段沿用原有字段命名 `clause`，内容填标准名称。
                clause=standard_name or "标准名称未知",
                # 新增 `scope` 字段，展示标准适用范围（a330）。
                scope=scope or "适用范围未知",
            )
        )
        if len(citations) >= max_items:
            break

    return citations


def _decide_action(citations: list[CitationPayload]) -> Literal["continue", "clarify"]:
    """根据是否有引用决定 action。"""

    return "continue" if citations else "clarify"


@lru_cache(maxsize=8)
def get_llm(model_id: str) -> ChatOpenAI:
    """按模型 ID 获取大模型客户端（多模型缓存）。"""

    model_config = resolve_chat_model(model_id)
    if not model_config.api_key:
        raise ValueError(
            f"模型 `{model_config.model_id}` 缺少 API Key，请检查环境变量配置。"
        )
    return ChatOpenAI(
        model=model_config.model_name,
        api_key=model_config.api_key,
        base_url=model_config.base_url,
        temperature=get_llm_temperature(),
        timeout=get_llm_timeout_seconds(),
    )


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """获取 Redis 客户端（单例缓存）。"""

    return Redis.from_url(get_redis_url(), decode_responses=True)


def _get_session_history(session_key: str) -> BaseChatMessageHistory:
    """按会话键返回 Redis 持久化历史。"""

    return RedisChatMessageHistory(
        redis_client=get_redis_client(),
        session_key=session_key,
        key_prefix=get_memory_key_prefix(),
        ttl_seconds=get_memory_ttl_seconds(),
        max_messages=get_memory_max_messages(),
    )


@lru_cache(maxsize=8)
def get_memory_chain(model_id: str) -> RunnableWithMessageHistory:
    """按模型 ID 构建带 Memory 的问答链路（Prompt -> LLM -> 文本解析）。"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            (
                "human",
                (
                    "用户问题：\n{query}\n\n"
                    "检索上下文：\n{retrieved_context}\n\n"
                    "请只依据检索上下文与对话历史回答。"
                ),
            ),
        ]
    )

    base_chain = prompt | get_llm(model_id) | StrOutputParser()
    return RunnableWithMessageHistory(
        base_chain,
        _get_session_history,
        input_messages_key="query",
        history_messages_key="history",
    )


def ask_standard_assistant(query: str, session_key: str, model_id: str | None = None) -> QAResult:
    """非流式问答：先检索，再生成，最终返回回答与引用。"""

    model_config = resolve_chat_model(model_id)
    retrieved_records = retrieve_standards(query=query)
    retrieved_context = build_retrieval_context(retrieved_records)
    citations = _build_citations(retrieved_records)
    action = _decide_action(citations)

    result = get_memory_chain(model_config.model_id).invoke(
        {
            "query": query,
            "retrieved_context": retrieved_context,
        },
        config={"configurable": {"session_id": session_key}},
    )
    answer = result.strip()
    if not answer:
        answer = "没有生成有效回答，请重试。"

    return QAResult(
        answer=answer,
        citations=citations,
        action=action,
        retrieved_count=len(retrieved_records),
        model_id=model_config.model_id,
        model_name=model_config.display_name,
        provider=model_config.provider,
    )


def stream_standard_assistant(
    query: str, session_key: str, model_id: str | None = None
) -> QAStreamResult:
    """流式问答：先检索，再生成流式分片，最后回传引用。"""

    model_config = resolve_chat_model(model_id)
    retrieved_records = retrieve_standards(query=query)
    retrieved_context = build_retrieval_context(retrieved_records)
    citations = _build_citations(retrieved_records)
    action = _decide_action(citations)

    chain = get_memory_chain(model_config.model_id)

    def _stream() -> Iterator[str]:
        """内部流式迭代器：逐块输出模型文本。"""
        for chunk in chain.stream(
            {
                "query": query,
                "retrieved_context": retrieved_context,
            },
            config={"configurable": {"session_id": session_key}},
        ):
            if chunk:
                yield chunk

    return QAStreamResult(
        chunks=_stream(),
        citations=citations,
        action=action,
        retrieved_count=len(retrieved_records),
        model_id=model_config.model_id,
        model_name=model_config.display_name,
        provider=model_config.provider,
    )
