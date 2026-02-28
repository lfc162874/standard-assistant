"""配置读取模块：统一从环境变量读取后端运行所需参数。"""

import os

from dotenv import load_dotenv

load_dotenv()


def get_deepseek_api_key() -> str:
    """读取 DeepSeek API Key。"""

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing DEEPSEEK_API_KEY")
    return api_key


def get_deepseek_model() -> str:
    """读取 DeepSeek 模型名。"""

    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()


def get_deepseek_base_url() -> str:
    """读取 DeepSeek 接口地址。"""

    return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()


def get_llm_temperature() -> float:
    """读取并解析 LLM temperature。"""

    raw_value = os.getenv("LLM_TEMPERATURE", "0.2").strip()
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError("LLM_TEMPERATURE must be a float") from exc


def get_llm_timeout_seconds() -> float:
    """读取并解析 LLM 超时时间（秒）。"""

    raw_value = os.getenv("LLM_TIMEOUT_SECONDS", "60").strip()
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError("LLM_TIMEOUT_SECONDS must be a number") from exc


def get_redis_url() -> str:
    """读取 Redis 连接地址。"""

    return os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()


def get_memory_key_prefix() -> str:
    """读取会话记忆 key 前缀。"""

    return os.getenv("MEMORY_KEY_PREFIX", "standard_assistant:history").strip()


def get_memory_ttl_seconds() -> int:
    """读取会话记忆过期时间（秒）。"""

    raw_value = os.getenv("MEMORY_TTL_SECONDS", "86400").strip()
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("MEMORY_TTL_SECONDS must be an integer") from exc


def get_memory_max_messages() -> int:
    """读取单会话最大保留消息数。"""

    raw_value = os.getenv("MEMORY_MAX_MESSAGES", "40").strip()
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("MEMORY_MAX_MESSAGES must be an integer") from exc


def get_embedding_api_key() -> str:
    """读取 Embedding API Key。"""

    api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing EMBEDDING_API_KEY")
    return api_key


def get_embedding_model() -> str:
    """读取 Embedding 模型名。"""

    return os.getenv("EMBEDDING_MODEL", "text-embedding-v4").strip()


def get_embedding_base_url() -> str:
    """读取 Embedding 接口地址。"""

    return os.getenv(
        "EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ).strip()


def get_chroma_persist_dir() -> str:
    """读取 Chroma 本地持久化目录。"""

    return os.getenv("CHROMA_PERSIST_DIR", "./chroma_data").strip()


def get_chroma_collection() -> str:
    """读取 Chroma 集合名称。"""

    return os.getenv("CHROMA_COLLECTION", "standards_meta_v1").strip()


def get_rag_top_k() -> int:
    """读取向量检索 TopK。"""

    raw_value = os.getenv("RAG_TOP_K", "5").strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("RAG_TOP_K must be an integer") from exc
    if value <= 0:
        raise ValueError("RAG_TOP_K must be positive")
    return value
