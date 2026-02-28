from __future__ import annotations

"""模型注册与选择服务：统一管理可用聊天模型列表与切换逻辑。"""
from dataclasses import dataclass
from functools import lru_cache

from app.core.settings import (
    get_chat_enabled_models,
    get_deepseek_api_key,
    get_deepseek_base_url,
    get_deepseek_model,
    get_default_chat_model_id,
    get_qwen_api_key,
    get_qwen_base_url,
    get_qwen_model,
)


class UnsupportedModelError(ValueError):
    """请求了不支持的模型 ID。"""


@dataclass(frozen=True)
class ChatModelConfig:
    """单个可切换聊天模型配置。"""

    model_id: str
    display_name: str
    provider: str
    model_name: str
    base_url: str
    api_key: str


def _build_builtin_registry() -> dict[str, ChatModelConfig]:
    """
    构建内置模型注册表。

    当前默认提供模型入口：
    - deepseek-chat
    - deepseek-reasoner
    - qwen-plus
    """

    deepseek_base_url = get_deepseek_base_url()
    # DeepSeek 仍复用当前系统已有的 DEEPSEEK_API_KEY。
    # 这里只读取可选值，避免在未使用该模型时阻断系统启动。
    try:
        deepseek_key = get_deepseek_api_key()
    except Exception:
        deepseek_key = ""

    qwen_base_url = get_qwen_base_url()
    qwen_key = get_qwen_api_key()
    qwen_model = get_qwen_model()

    registry: dict[str, ChatModelConfig] = {
        "deepseek-chat": ChatModelConfig(
            model_id="deepseek-chat",
            display_name="DeepSeek Chat",
            provider="deepseek",
            model_name="deepseek-chat",
            base_url=deepseek_base_url,
            api_key=deepseek_key,
        ),
        "deepseek-reasoner": ChatModelConfig(
            model_id="deepseek-reasoner",
            display_name="DeepSeek Reasoner",
            provider="deepseek",
            model_name="deepseek-reasoner",
            base_url=deepseek_base_url,
            api_key=deepseek_key,
        ),
        "qwen3.5-plus": ChatModelConfig(
            model_id="qwen3.5-plus",
            display_name="qwen3.5-plus",
            provider="qwen",
            model_name=qwen_model,
            base_url=qwen_base_url,
            api_key=qwen_key,
        ),
    }

    # 兼容历史默认配置：若 DEEPSEEK_MODEL 覆盖了 deepseek-chat，则同步到默认入口。
    overridden_model = get_deepseek_model()
    if overridden_model and overridden_model != "deepseek-chat":
        registry["deepseek-chat"] = ChatModelConfig(
            model_id="deepseek-chat",
            display_name=f"DeepSeek ({overridden_model})",
            provider="deepseek",
            model_name=overridden_model,
            base_url=deepseek_base_url,
            api_key=deepseek_key,
        )

    return registry


@lru_cache(maxsize=1)
def get_available_chat_models() -> list[ChatModelConfig]:
    """返回当前可切换模型列表。"""

    registry = _build_builtin_registry()
    enabled_ids = get_chat_enabled_models()
    if not enabled_ids:
        enabled_ids = [get_default_chat_model_id()]

    models: list[ChatModelConfig] = []
    for model_id in enabled_ids:
        config = registry.get(model_id)
        if config is not None:
            models.append(config)
    return models


def get_default_chat_model() -> ChatModelConfig:
    """返回默认模型配置；若默认模型无效则回退到第一个可用模型。"""

    models = get_available_chat_models()
    if not models:
        raise ValueError("未配置可用聊天模型，请检查 CHAT_ENABLED_MODELS")

    default_model_id = get_default_chat_model_id()
    for config in models:
        if config.model_id == default_model_id:
            return config

    return models[0]


def resolve_chat_model(model_id: str | None) -> ChatModelConfig:
    """根据请求 model_id 解析实际使用模型。"""

    models = get_available_chat_models()
    if not models:
        raise ValueError("未配置可用聊天模型，请检查 CHAT_ENABLED_MODELS")

    if not model_id:
        return get_default_chat_model()

    normalized_id = model_id.strip()
    for config in models:
        if config.model_id == normalized_id:
            return config

    supported = ", ".join(item.model_id for item in models)
    raise UnsupportedModelError(
        f"Unsupported model_id: `{normalized_id}`. Supported: {supported}"
    )
