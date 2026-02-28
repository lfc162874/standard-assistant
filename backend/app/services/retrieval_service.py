from __future__ import annotations

"""向量检索服务：负责查询 Chroma 并构造可注入 Prompt 的检索上下文。"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import chromadb
from langchain_openai import OpenAIEmbeddings

from app.core.settings import (
    get_chroma_collection,
    get_chroma_persist_dir,
    get_embedding_api_key,
    get_embedding_base_url,
    get_embedding_model,
    get_rag_top_k,
)


@dataclass
class RetrievedStandard:
    """单条检索命中记录。"""

    record_id: str
    document: str
    metadata: dict[str, Any]
    distance: float | None


def _safe_text(value: Any) -> str:
    """统一安全转字符串，避免 None/非字符串类型带来的处理分支。"""

    if value is None:
        return ""
    return str(value).strip()


@lru_cache(maxsize=1)
def get_embedding_client() -> OpenAIEmbeddings:
    """获取 embedding 客户端（单例缓存）。"""

    return OpenAIEmbeddings(
        model=get_embedding_model(),
        api_key=get_embedding_api_key(),
        base_url=get_embedding_base_url(),
        # 使用纯文本输入模式，增强 OpenAI 兼容接口稳定性。
        tiktoken_enabled=False,
        check_embedding_ctx_length=False,
    )


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    """获取本地 Chroma 客户端（单例缓存）。"""

    return chromadb.PersistentClient(path=get_chroma_persist_dir())


def _get_collection_or_none():
    """获取集合；若不存在则返回 None，避免直接抛错中断主流程。"""

    try:
        return get_chroma_client().get_collection(name=get_chroma_collection())
    except Exception:
        return None


def retrieve_standards(query: str, top_k: int | None = None) -> list[RetrievedStandard]:
    """按问题做向量检索，返回结构化命中结果列表。"""

    normalized_query = query.strip()
    if not normalized_query:
        return []

    collection = _get_collection_or_none()
    if collection is None:
        return []

    query_vector = get_embedding_client().embed_query(normalized_query)
    result = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k or get_rag_top_k(),
        include=["documents", "metadatas", "distances"],
    )

    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    retrieved: list[RetrievedStandard] = []
    for idx, item_id in enumerate(ids):
        metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
        document = docs[idx] if idx < len(docs) and docs[idx] else ""
        raw_distance = distances[idx] if idx < len(distances) else None
        distance = float(raw_distance) if raw_distance is not None else None
        retrieved.append(
            RetrievedStandard(
                record_id=_safe_text(item_id),
                document=_safe_text(document),
                metadata=metadata,
                distance=distance,
            )
        )

    return retrieved


def build_retrieval_context(records: list[RetrievedStandard]) -> str:
    """将检索结果拼装成可注入 Prompt 的上下文文本。"""

    if not records:
        return "未检索到相关标准元信息。"

    blocks: list[str] = []
    for idx, record in enumerate(records, start=1):
        meta = record.metadata
        block = [
            f"[{idx}]",
            f"标准号: {_safe_text(meta.get('a100')) or '未知'}",
            f"标准名称: {_safe_text(meta.get('a298')) or '未知'}",
            f"发布日期: {_safe_text(meta.get('a101')) or '未知'}",
            f"中国标准分类（中文）: {_safe_text(meta.get('a825cn')) or '未知'}",
            f"国际标准分类（中文）: {_safe_text(meta.get('a826cn')) or '未知'}",
            f"适用范围: {_safe_text(meta.get('a330')) or '未知'}",
            f"向量距离: {record.distance if record.distance is not None else '未知'}",
        ]
        if record.document:
            block.append(f"原始向量文本: {record.document}")
        blocks.append("\n".join(block))

    return "\n\n".join(blocks)
