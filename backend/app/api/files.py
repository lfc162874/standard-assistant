"""文件上传接口：支持文本文件上传到 OSS 并触发 GLM-OCR。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.auth_service import get_current_user
from app.services.file_upload_service import (
    FileValidationError,
    OcrProcessError,
    OssUploadError,
    process_text_upload,
)
from app.services.user_service import UserRecord

router = APIRouter()


class UploadTextResponse(BaseModel):
    """文本上传并识别接口响应。"""

    file_id: str
    file_name: str
    file_ext: str
    file_size: int
    content_type: str
    session_id: str | None = None
    oss_key: str
    oss_url: str
    preview_text: str
    ocr_summary: str
    ocr_keywords: list[str] = Field(default_factory=list)
    ocr_structured: dict[str, Any] = Field(default_factory=dict)
    timestamp: str


@router.post("/files/upload-text", response_model=UploadTextResponse)
async def upload_text_file(
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
) -> UploadTextResponse:
    """上传文本文件到 OSS，并触发 GLM-OCR 提取结构化信息。"""

    file_name = file.filename or "upload.txt"
    content_type = file.content_type or "application/octet-stream"
    file_content = await file.read()

    try:
        result = process_text_upload(
            user_id=current_user.id,
            session_id=session_id,
            file_name=file_name,
            content_type=content_type,
            file_content=file_content,
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OssUploadError as exc:
        raise HTTPException(status_code=502, detail=f"OSS 上传失败: {exc}") from exc
    except OcrProcessError as exc:
        raise HTTPException(status_code=502, detail=f"GLM-OCR 处理失败: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"配置错误: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"上传处理失败: {exc}") from exc

    return UploadTextResponse(
        file_id=result.file_id,
        file_name=result.file_name,
        file_ext=result.file_ext,
        file_size=result.file_size,
        content_type=result.content_type,
        session_id=result.session_id,
        oss_key=result.oss_key,
        oss_url=result.oss_url,
        preview_text=result.preview_text,
        ocr_summary=result.ocr_summary,
        ocr_keywords=result.ocr_keywords,
        ocr_structured=result.ocr_structured,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

