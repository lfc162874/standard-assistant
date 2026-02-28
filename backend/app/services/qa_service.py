from functools import lru_cache
from typing import Iterator

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from redis import Redis

from app.core.settings import (
    get_deepseek_api_key,
    get_deepseek_base_url,
    get_deepseek_model,
    get_llm_temperature,
    get_llm_timeout_seconds,
    get_memory_key_prefix,
    get_memory_max_messages,
    get_memory_ttl_seconds,
    get_redis_url,
)
from app.services.redis_history import RedisChatMessageHistory

SYSTEM_PROMPT = """
你是“标准智能助手”。
你的职责：
1. 基于用户问题给出清晰、准确、简洁的回答。
2. 在无法确认事实时明确说明“不确定”，并建议用户补充标准编号或上下文。
3. 不要编造不存在的标准编号、条款或实施日期。
4. 输出使用中文。
""".strip()


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    # 复用同一个 LLM 客户端，避免每次请求重复初始化连接与配置。
    return ChatOpenAI(
        model=get_deepseek_model(),
        api_key=get_deepseek_api_key(),
        base_url=get_deepseek_base_url(),
        temperature=get_llm_temperature(),
        timeout=get_llm_timeout_seconds(),
    )


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    # decode_responses=True: Redis 直接返回字符串，简化 JSON 序列化处理。
    return Redis.from_url(get_redis_url(), decode_responses=True)


def _get_session_history(session_key: str) -> BaseChatMessageHistory:
    return RedisChatMessageHistory(
        redis_client=get_redis_client(),
        session_key=session_key,
        key_prefix=get_memory_key_prefix(),
        ttl_seconds=get_memory_ttl_seconds(),
        max_messages=get_memory_max_messages(),
    )


@lru_cache(maxsize=1)
def get_memory_chain() -> RunnableWithMessageHistory:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{query}"),
        ]
    )

    # Prompt -> LLM -> 文本解析；通过 RunnableWithMessageHistory 自动维护历史消息。
    base_chain = prompt | get_llm() | StrOutputParser()
    return RunnableWithMessageHistory(
        base_chain,
        _get_session_history,
        input_messages_key="query",
        history_messages_key="history",
    )


def ask_standard_assistant(query: str, session_key: str) -> str:
    chain = get_memory_chain()
    result = chain.invoke(
        {"query": query},
        config={"configurable": {"session_id": session_key}},
    )
    answer = result.strip()
    return answer if answer else "没有生成有效回答，请重试。"


def stream_standard_assistant(query: str, session_key: str) -> Iterator[str]:
    # 流式输出同样走带记忆的链路，确保多轮上下文对齐。
    chain = get_memory_chain()
    for chunk in chain.stream(
        {"query": query},
        config={"configurable": {"session_id": session_key}},
    ):
        if chunk:
            yield chunk
