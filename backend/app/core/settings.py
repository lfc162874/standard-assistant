import os

from dotenv import load_dotenv

load_dotenv()


def get_deepseek_api_key() -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing DEEPSEEK_API_KEY")
    return api_key


def get_deepseek_model() -> str:
    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()


def get_deepseek_base_url() -> str:
    return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()


def get_llm_temperature() -> float:
    raw_value = os.getenv("LLM_TEMPERATURE", "0.2").strip()
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError("LLM_TEMPERATURE must be a float") from exc


def get_llm_timeout_seconds() -> float:
    raw_value = os.getenv("LLM_TIMEOUT_SECONDS", "60").strip()
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError("LLM_TIMEOUT_SECONDS must be a number") from exc


def get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()


def get_memory_key_prefix() -> str:
    return os.getenv("MEMORY_KEY_PREFIX", "standard_assistant:history").strip()


def get_memory_ttl_seconds() -> int:
    raw_value = os.getenv("MEMORY_TTL_SECONDS", "86400").strip()
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("MEMORY_TTL_SECONDS must be an integer") from exc


def get_memory_max_messages() -> int:
    raw_value = os.getenv("MEMORY_MAX_MESSAGES", "40").strip()
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("MEMORY_MAX_MESSAGES must be an integer") from exc
