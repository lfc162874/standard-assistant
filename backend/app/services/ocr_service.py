from __future__ import annotations

"""GLM-OCR 服务：将文本转换为结构化信息。"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI

from app.core.settings import (
    get_glm_ocr_api_key,
    get_glm_ocr_base_url,
    get_glm_ocr_model,
    get_llm_timeout_seconds,
)


class OcrProcessError(RuntimeError):
    """OCR 处理异常。"""


@dataclass(frozen=True)
class OcrResult:
    """OCR 输出结构。"""

    summary: str
    keywords: list[str]
    structured: dict[str, Any]
    raw_output: str


@lru_cache(maxsize=1)
def get_glm_ocr_client() -> ChatOpenAI:
    """构建 GLM-OCR 客户端。"""

    return ChatOpenAI(
        model=get_glm_ocr_model(),
        api_key=get_glm_ocr_api_key(),
        base_url=get_glm_ocr_base_url(),
        temperature=0.1,
        timeout=get_llm_timeout_seconds(),
    )


def _to_text(content: Any) -> str:
    """将模型返回内容统一转为文本。"""

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
        return "\n".join(parts).strip()
    return str(content).strip()


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    """尽量从模型输出中提取 JSON。"""

    text = raw_text.strip()
    if not text:
        return {}

    fenced = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1).strip() if fenced else text

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 回退：尝试提取首个 JSON 对象。
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        try:
            parsed = json.loads(obj_match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {}


def extract_text_with_glm_ocr(text: str, file_name: str) -> OcrResult:
    """调用 GLM-OCR 对文本做结构化提取。"""

    if not text.strip():
        raise OcrProcessError("文本内容为空，无法执行 OCR 识别")

    prompt = (
        "你是 GLM-OCR 结构化提取助手。"
        "请对下面的文本进行识别与结构化提取，并仅返回 JSON。"
        "JSON schema 必须包含："
        "`summary`(字符串), `keywords`(字符串数组), `structured`(对象)。\n\n"
        f"文件名：{file_name}\n"
        "待识别文本：\n"
        f"{text}"
    )

    try:
        response = get_glm_ocr_client().invoke(prompt)
    except Exception as exc:  # pragma: no cover - 外部服务调用
        raise OcrProcessError(f"GLM-OCR 调用失败: {exc}") from exc

    raw_output = _to_text(getattr(response, "content", ""))
    payload = _extract_json_payload(raw_output)

    summary = str(payload.get("summary", "")).strip() or "未提取到摘要"
    raw_keywords = payload.get("keywords", [])
    keywords = [str(item).strip() for item in raw_keywords if str(item).strip()] if isinstance(raw_keywords, list) else []

    structured = payload.get("structured", {})
    if not isinstance(structured, dict):
        structured = {"raw_structured": structured}

    return OcrResult(
        summary=summary,
        keywords=keywords,
        structured=structured,
        raw_output=raw_output,
    )

