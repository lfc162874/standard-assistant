from __future__ import annotations

"""阿里云 OSS 上传服务。"""

from dataclasses import dataclass
from functools import lru_cache

from app.core.settings import (
    get_aliyun_oss_access_key_id,
    get_aliyun_oss_access_key_secret,
    get_aliyun_oss_bucket,
    get_aliyun_oss_endpoint,
    get_aliyun_oss_public_base_url,
)

try:
    import oss2  # type: ignore
except ImportError:  # pragma: no cover - 运行时依赖检查
    oss2 = None  # type: ignore


class OssUploadError(RuntimeError):
    """OSS 上传异常。"""


@dataclass(frozen=True)
class OssUploadResult:
    """OSS 上传结果。"""

    object_key: str
    oss_url: str


def _normalize_endpoint(endpoint: str) -> str:
    """标准化 endpoint，保证带协议。"""

    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"https://{endpoint}"


def _build_public_url(object_key: str) -> str:
    """构建可访问 URL。"""

    custom_base = get_aliyun_oss_public_base_url()
    if custom_base:
        return f"{custom_base.rstrip('/')}/{object_key}"

    endpoint = get_aliyun_oss_endpoint().replace("https://", "").replace("http://", "")
    bucket = get_aliyun_oss_bucket()
    return f"https://{bucket}.{endpoint}/{object_key}"


@lru_cache(maxsize=1)
def get_oss_bucket():
    """获取 OSS bucket 客户端。"""

    if oss2 is None:
        raise OssUploadError("缺少 `oss2` 依赖，请先执行 `pip install -r requirements.txt`")

    auth = oss2.Auth(
        get_aliyun_oss_access_key_id(),
        get_aliyun_oss_access_key_secret(),
    )
    return oss2.Bucket(
        auth,
        _normalize_endpoint(get_aliyun_oss_endpoint()),
        get_aliyun_oss_bucket(),
    )


def upload_bytes_to_oss(object_key: str, content: bytes, content_type: str) -> OssUploadResult:
    """上传字节内容到 OSS。"""

    bucket = get_oss_bucket()
    try:
        response = bucket.put_object(
            object_key,
            content,
            headers={"Content-Type": content_type},
        )
    except Exception as exc:  # pragma: no cover - 外部服务调用
        raise OssUploadError(f"OSS 上传失败: {exc}") from exc

    status = getattr(response, "status", 0)
    if not (200 <= int(status) < 300):
        raise OssUploadError(f"OSS 上传失败: HTTP {status}")

    return OssUploadResult(
        object_key=object_key,
        oss_url=_build_public_url(object_key),
    )

