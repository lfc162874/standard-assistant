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


def get_qwen_api_key() -> str:
    """读取 Qwen API Key（可选）。"""

    return os.getenv("QWEN_API_KEY", "").strip()


def get_qwen_model() -> str:
    """读取 Qwen 模型名。"""

    return os.getenv("QWEN_MODEL", "qwen-plus").strip()


def get_qwen_base_url() -> str:
    """读取 Qwen 接口地址。"""

    return os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ).strip()


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


def get_default_chat_model_id() -> str:
    """读取默认聊天模型 ID。"""

    return os.getenv("DEFAULT_CHAT_MODEL_ID", "deepseek-chat").strip()


def get_chat_enabled_models() -> list[str]:
    """读取启用的模型 ID 列表（逗号分隔）。"""

    raw_value = os.getenv(
        "CHAT_ENABLED_MODELS", "deepseek-chat,deepseek-reasoner,qwen-plus"
    ).strip()
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_db_url() -> str:
    """读取 PostgreSQL 连接地址。"""

    return os.getenv(
        "DB_URL", "postgresql://postgres:postgres@localhost:5432/standard_assistant"
    ).strip()


def get_jwt_secret_key() -> str:
    """读取 JWT 签名密钥。"""

    return os.getenv("JWT_SECRET_KEY", "change-me-in-production").strip()


def get_access_token_expire_minutes() -> int:
    """读取 Access Token 过期分钟数。"""

    raw_value = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30").strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer") from exc
    if value <= 0:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
    return value


def get_refresh_token_expire_days() -> int:
    """读取 Refresh Token 过期天数。"""

    raw_value = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14").strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be an integer") from exc
    if value <= 0:
        raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be positive")
    return value


def get_auth_register_enabled() -> bool:
    """读取是否允许注册。"""

    raw_value = os.getenv("AUTH_REGISTER_ENABLED", "true").strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def get_login_max_retries() -> int:
    """读取登录失败锁定阈值。"""

    raw_value = os.getenv("LOGIN_MAX_RETRIES", "5").strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("LOGIN_MAX_RETRIES must be an integer") from exc
    if value <= 0:
        raise ValueError("LOGIN_MAX_RETRIES must be positive")
    return value


def get_login_lock_minutes() -> int:
    """读取登录锁定分钟数。"""

    raw_value = os.getenv("LOGIN_LOCK_MINUTES", "15").strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("LOGIN_LOCK_MINUTES must be an integer") from exc
    if value <= 0:
        raise ValueError("LOGIN_LOCK_MINUTES must be positive")
    return value
