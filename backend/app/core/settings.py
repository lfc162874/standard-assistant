"""配置读取模块：统一从环境变量读取后端运行所需参数。"""

import os
import re
from urllib.parse import quote

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


def get_glm_ocr_api_key() -> str:
    """读取 GLM-OCR API Key。"""

    api_key = os.getenv("GLM_OCR_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing GLM_OCR_API_KEY")
    return api_key


def get_glm_ocr_base_url() -> str:
    """读取 GLM-OCR 接口地址。"""

    return os.getenv("GLM_OCR_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").strip()


def get_glm_ocr_model() -> str:
    """读取 GLM-OCR 模型名。"""

    return os.getenv("GLM_OCR_MODEL", "glm-4.1v-thinking-flash").strip()


def get_upload_max_bytes() -> int:
    """读取上传文件大小上限（字节）。"""

    raw_value = os.getenv("UPLOAD_MAX_BYTES", str(5 * 1024 * 1024)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("UPLOAD_MAX_BYTES must be an integer") from exc
    if value <= 0:
        raise ValueError("UPLOAD_MAX_BYTES must be positive")
    return value


def get_upload_max_text_chars() -> int:
    """读取上传文本可解析字符上限。"""

    raw_value = os.getenv("UPLOAD_MAX_TEXT_CHARS", "60000").strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("UPLOAD_MAX_TEXT_CHARS must be an integer") from exc
    if value <= 0:
        raise ValueError("UPLOAD_MAX_TEXT_CHARS must be positive")
    return value


def get_upload_allowed_text_exts() -> list[str]:
    """读取允许上传的文本扩展名。"""

    raw_value = os.getenv("UPLOAD_ALLOWED_TEXT_EXTS", "txt,md,csv,json").strip()
    if not raw_value:
        return ["txt", "md", "csv", "json"]
    result: list[str] = []
    for item in raw_value.split(","):
        normalized = item.strip().lower().lstrip(".")
        if normalized:
            result.append(normalized)
    return result or ["txt", "md", "csv", "json"]


def get_aliyun_oss_endpoint() -> str:
    """读取阿里云 OSS endpoint。"""

    endpoint = os.getenv("ALIYUN_OSS_ENDPOINT", "").strip()
    if not endpoint:
        raise ValueError("Missing ALIYUN_OSS_ENDPOINT")
    return endpoint


def get_aliyun_oss_region() -> str:
    """读取阿里云 OSS 区域。"""

    return os.getenv("ALIYUN_OSS_REGION", "cn-hangzhou").strip()


def get_aliyun_oss_bucket() -> str:
    """读取阿里云 OSS bucket 名称。"""

    bucket = os.getenv("ALIYUN_OSS_BUCKET", "").strip()
    if not bucket:
        raise ValueError("Missing ALIYUN_OSS_BUCKET")
    return bucket


def get_aliyun_oss_access_key_id() -> str:
    """读取阿里云 OSS AccessKey ID。"""

    access_key_id = os.getenv("ALIYUN_OSS_ACCESS_KEY_ID", "").strip()
    if not access_key_id:
        raise ValueError("Missing ALIYUN_OSS_ACCESS_KEY_ID")
    return access_key_id


def get_aliyun_oss_access_key_secret() -> str:
    """读取阿里云 OSS AccessKey Secret。"""

    access_key_secret = os.getenv("ALIYUN_OSS_ACCESS_KEY_SECRET", "").strip()
    if not access_key_secret:
        raise ValueError("Missing ALIYUN_OSS_ACCESS_KEY_SECRET")
    return access_key_secret


def get_aliyun_oss_object_prefix() -> str:
    """读取阿里云 OSS 对象前缀。"""

    return os.getenv("ALIYUN_OSS_OBJECT_PREFIX", "standard-assistant/uploads/text").strip()


def get_aliyun_oss_public_base_url() -> str:
    """读取可选 OSS 公网访问域名前缀。"""

    return os.getenv("ALIYUN_OSS_PUBLIC_BASE_URL", "").strip()


def get_pg_host() -> str:
    """读取 PostgreSQL 主机地址。"""

    return os.getenv("PG_HOST", "localhost").strip()


def get_pg_port() -> int:
    """读取 PostgreSQL 端口。"""

    raw_value = os.getenv("PG_PORT", "5432").strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("PG_PORT must be an integer") from exc
    if value <= 0:
        raise ValueError("PG_PORT must be positive")
    return value


def get_pg_user() -> str:
    """读取 PostgreSQL 用户名。"""

    return os.getenv("PG_USER", "postgres").strip()


def get_pg_password() -> str:
    """读取 PostgreSQL 密码。"""

    return os.getenv("PG_PASSWORD", "123456").strip()


def get_pg_database() -> str:
    """读取 PostgreSQL 数据库名。"""

    return os.getenv("PG_DATABASE", "postgres").strip()


def get_pg_schema() -> str:
    """读取 PostgreSQL schema。"""

    schema = os.getenv("PG_SCHEMA", "public").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
        raise ValueError("PG_SCHEMA contains invalid characters")
    return schema


def get_db_url() -> str:
    """根据 PG_* 配置构建 PostgreSQL 连接地址。"""

    user = quote(get_pg_user(), safe="")
    password = quote(get_pg_password(), safe="")
    host = get_pg_host()
    port = get_pg_port()
    database = quote(get_pg_database(), safe="")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


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
