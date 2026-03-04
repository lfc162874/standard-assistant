from __future__ import annotations

"""文本文件上传编排服务：校验 -> OSS -> GLM-OCR。"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from app.core.settings import (
    get_aliyun_oss_object_prefix,
    get_upload_allowed_text_exts,
    get_upload_max_bytes,
    get_upload_max_text_chars,
)
from app.services.ocr_service import OcrProcessError, extract_text_with_glm_ocr
from app.services.oss_service import OssUploadError, upload_bytes_to_oss


class FileValidationError(ValueError):
    """文件校验异常。"""


@dataclass(frozen=True)
class TextUploadPipelineResult:
    """上传与识别最终结果。"""

    file_id: str
    file_name: str
    file_ext: str
    file_size: int
    content_type: str
    session_id: str | None
    oss_key: str
    oss_url: str
    preview_text: str
    ocr_summary: str
    ocr_keywords: list[str]
    ocr_structured: dict[str, Any]
    ocr_raw_output: str


def _safe_filename(file_name: str) -> str:
    """将文件名归一化为安全字符串。"""

    name = file_name.strip() or "upload.txt"
    return re.sub(r"[^0-9A-Za-z._-]+", "_", name)


def _detect_file_ext(file_name: str) -> str:
    """获取文件扩展名。"""

    suffix = Path(file_name).suffix.lower().lstrip(".")
    return suffix


def _is_allowed_mime(content_type: str, file_ext: str) -> bool:
    """校验 MIME 是否与文本文件匹配。"""

    mime = (content_type or "").lower().strip()
    if not mime or mime == "application/octet-stream":
        return True
    if mime.startswith("text/"):
        return True
    if mime in {"application/json", "application/csv", "application/vnd.ms-excel"}:
        return True
    # 按扩展名兜底允许。
    return file_ext in {"txt", "md", "csv", "json"}


def _decode_text(content: bytes) -> str:
    """按 UTF-8 优先解码，失败则尝试 GB18030。"""

    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise FileValidationError("文本解码失败，仅支持 UTF-8/GB18030 编码文本")


def _normalize_text(text: str) -> str:
    """清洗文本内容。"""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    cleaned = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F]", "", cleaned)
    return cleaned.strip()


def process_text_upload(
    *,
    user_id: str,
    session_id: str | None,
    file_name: str,
    content_type: str,
    file_content: bytes,
) -> TextUploadPipelineResult:
    """执行文本上传与 GLM-OCR 识别完整流程。"""

    file_size = len(file_content)
    max_bytes = get_upload_max_bytes()
    if file_size <= 0:
        raise FileValidationError("上传文件为空")
    if file_size > max_bytes:
        raise FileValidationError(f"文件过大，当前上限 {max_bytes} 字节")

    file_ext = _detect_file_ext(file_name)
    allowed_exts = set(get_upload_allowed_text_exts())
    if file_ext not in allowed_exts:
        raise FileValidationError(f"不支持的文件类型 `{file_ext}`，仅支持: {', '.join(sorted(allowed_exts))}")
    if not _is_allowed_mime(content_type, file_ext):
        raise FileValidationError(f"文件 MIME 不匹配: {content_type}")

    decoded_text = _normalize_text(_decode_text(file_content))
    if not decoded_text:
        raise FileValidationError("文件文本内容为空")

    max_chars = get_upload_max_text_chars()
    truncated_text = decoded_text[:max_chars]

    file_id = str(uuid4())
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y/%m/%d")
    safe_name = _safe_filename(file_name)
    object_key = f"{get_aliyun_oss_object_prefix().strip('/')}/{date_prefix}/{user_id}/{file_id}_{safe_name}"

    upload_result = upload_bytes_to_oss(
        object_key=object_key,
        content=file_content,
        content_type=content_type or "text/plain",
    )

    ocr_result = extract_text_with_glm_ocr(
        text=truncated_text,
        file_name=safe_name,
    )

    return TextUploadPipelineResult(
        file_id=file_id,
        file_name=safe_name,
        file_ext=file_ext,
        file_size=file_size,
        content_type=content_type or "text/plain",
        session_id=session_id,
        oss_key=upload_result.object_key,
        oss_url=upload_result.oss_url,
        preview_text=truncated_text[:800],
        ocr_summary=ocr_result.summary,
        ocr_keywords=ocr_result.keywords,
        ocr_structured=ocr_result.structured,
        ocr_raw_output=ocr_result.raw_output,
    )


__all__ = [
    "FileValidationError",
    "OcrProcessError",
    "OssUploadError",
    "TextUploadPipelineResult",
    "process_text_upload",
]

