#!/usr/bin/env python3
from __future__ import annotations

"""
标准元信息向量化脚本（PostgreSQL -> Embedding -> Chroma）。

脚本职责：
1. 从 `drms_standard_middle_sync` 读取标准元信息。
2. 将每条记录拼成一段可向量化文本。
3. 调用 `text-embedding-v4` 生成向量。
4. 将向量与元数据写入本地 Chroma 集合。

注意：
- 不依赖 `is_deleted` / `update_time` 字段。
- 支持 `--count`，可先导入部分数据（例如 10000 条）验证效果。
"""

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
import psycopg
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from psycopg import sql
from psycopg.rows import dict_row


# 用于构造向量文本的字段：
# 左侧是 PostgreSQL 字段名，右侧是拼装到文本中的中文标签。
CONTENT_FIELDS = [
    ("a100", "标准号"),
    ("a298", "标准名称"),
    ("a101", "发布日期"),
    ("a205", "实施日期"),
    ("a206", "作废日期"),
    ("a000", "标准状态"),
    ("a200", "标准细分状态"),
    ("a825cn", "中国标准分类（中文）"),
    ("a826cn", "国际标准分类（中文）"),
    ("a330", "适用范围"),
]

# 写入 Chroma metadata 的字段（用于展示、筛选、追踪）。
METADATA_FIELDS = [
    "id",
    "a100",
    "a298",
    "a101",
    "a205",
    "a206",
    "a000",
    "a200",
    "a825cn",
    "a826cn",
    "a330",
]


@dataclass
class RuntimeConfig:
    """运行配置：由命令行参数与环境变量共同组成。"""

    # PostgreSQL 连接与数据表位置
    pg_dsn: str
    pg_schema: str
    pg_table: str

    # Chroma 持久化目录与集合名
    chroma_dir: str
    chroma_collection: str

    # Embedding 服务配置
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str

    # 导入行为参数
    batch_size: int
    count: int | None
    truncate: bool
    dry_run: bool


def build_pg_dsn() -> str:
    """构造 psycopg DSN：优先读取 `PG_DSN`，否则使用 PG_* 拼接。"""

    # 最高优先级：直接使用显式 DSN。
    dsn = os.getenv("PG_DSN", "").strip()
    if dsn:
        return dsn

    # 兜底方案：从 host/port/user/password/database 拼接 DSN。
    host = os.getenv("PG_HOST", "localhost").strip()
    port = os.getenv("PG_PORT", "5432").strip()
    user = os.getenv("PG_USER", "postgres").strip()
    password = os.getenv("PG_PASSWORD", "123456").strip()
    database = os.getenv("PG_DATABASE", "postgres").strip()
    return (
        f"host={host} port={port} dbname={database} user={user} password={password}"
    )


def parse_args() -> RuntimeConfig:
    """解析命令行参数并生成最终运行配置。"""

    parser = argparse.ArgumentParser(
        description=(
            "Read standard metadata from PostgreSQL, build embeddings with "
            "text-embedding-v4, and upsert into local Chroma."
        )
    )

    # 同时兼容新参数 INGEST_COUNT 与旧参数 INGEST_LIMIT。
    default_count = int(
        os.getenv("INGEST_COUNT", os.getenv("INGEST_LIMIT", "0")).strip() or 0
    ) or None
    parser.add_argument(
        "--count",
        type=int,
        default=default_count,
        help="How many rows to ingest. Example: --count 10000",
    )
    parser.add_argument(
        "--limit",
        type=int,
        dest="count",
        # 兼容历史命令参数，但不在帮助信息中展示。
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("INGEST_BATCH_SIZE", "200").strip()),
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete target Chroma collection before ingesting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and build payloads only. Do not call embedding or Chroma upsert.",
    )
    args = parser.parse_args()

    # 参数基础校验，避免进入主流程后才报错。
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    if args.count is not None and args.count <= 0:
        raise ValueError("--count must be positive")

    return RuntimeConfig(
        pg_dsn=build_pg_dsn(),
        pg_schema=os.getenv("PG_SCHEMA", "public").strip(),
        pg_table=os.getenv("PG_TABLE", "drms_standard_middle_sync").strip(),
        chroma_dir=os.getenv("CHROMA_PERSIST_DIR", "./chroma_data").strip(),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "standards_meta_v1").strip(),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY", "").strip(),
        embedding_base_url=os.getenv(
            "EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ).strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-v4").strip(),
        batch_size=args.batch_size,
        count=args.count,
        truncate=args.truncate,
        dry_run=args.dry_run,
    )


def normalize_value(value: Any) -> str:
    """标准化字段值，统一转成可写入文本/metadata 的字符串。"""

    # 空值直接返回空字符串。
    if value is None:
        return ""
    # datetime 统一转为可读时间字符串。
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    # 其他类型统一转字符串并去除首尾空格。
    return str(value).strip()


def get_existing_columns(
    connection: psycopg.Connection[Any], schema: str, table: str
) -> set[str]:
    """读取表的实际字段名，用于后续动态选列和安全校验。"""

    sql_text = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(sql_text, (schema, table))
        rows = cursor.fetchall()
    return {row[0] for row in rows}


def build_document(row: dict[str, Any], available_fields: list[tuple[str, str]]) -> str:
    """将单行记录按模板字段拼装成一段向量文本。"""

    lines: list[str] = []
    for field, label in available_fields:
        value = normalize_value(row.get(field))
        # 空值不写入，减少噪声。
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def build_metadata(row: dict[str, Any], available_metadata_fields: list[str]) -> dict[str, Any]:
    """构造 Chroma metadata 字典。"""

    metadata: dict[str, Any] = {}
    for field in available_metadata_fields:
        value = normalize_value(row.get(field))
        # metadata 中不保留空值，避免冗余。
        if value:
            metadata[field] = value
    return metadata


def embed_documents_safe(embeddings: OpenAIEmbeddings, texts: list[str]) -> list[list[float]]:
    """
    生成向量（带兼容降级策略）。

    背景：
    - 某些 OpenAI 兼容服务会拒绝批量请求并返回
      `InvalidParameter / input.contents`。
    策略：
    - 先尝试 `embed_documents` 批量向量化。
    - 如遇兼容错误，自动降级为逐条 `embed_query`。
    """

    # 强制转为字符串列表，避免非字符串输入导致接口报错。
    normalized_texts = [text if isinstance(text, str) else str(text) for text in texts]
    try:
        # 首选路径：批量处理，吞吐更高。
        return embeddings.embed_documents(normalized_texts)
    except Exception as exc:
        error_message = str(exc)
        # 非已知兼容错误，直接抛出，避免吞掉真实问题。
        if "input.contents" not in error_message and "InvalidParameter" not in error_message:
            raise

        print(
            "[WARN] Batch embedding request failed with InvalidParameter. "
            "Fallback to single-text embedding mode."
        )
        vectors: list[list[float]] = []
        for text in normalized_texts:
            # 兼容路径：逐条向量化。
            vectors.append(embeddings.embed_query(text))
        return vectors


def get_select_query(
    columns: list[str],
    schema: str,
    table: str,
    count: int | None,
) -> tuple[sql.Composed, list[Any]]:
    """构造安全的查询语句（使用 sql.Identifier 防注入）。"""

    # 只查询必要字段，降低 IO 与内存占用。
    query = sql.SQL("SELECT {fields} FROM {table}").format(
        fields=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        table=sql.Identifier(schema, table),
    )
    params: list[Any] = []

    # 固定按 id 升序，保证导入顺序可复现。
    query += sql.SQL(" ORDER BY {column} ASC").format(column=sql.Identifier("id"))

    # 可选导入条数限制，便于分批测试。
    if count:
        query += sql.SQL(" LIMIT %s")
        params.append(count)

    return query, params


def get_collection(client: chromadb.PersistentClient, name: str, truncate: bool):
    """获取或创建 Chroma 集合；可选先删除旧集合。"""

    if truncate:
        try:
            client.delete_collection(name)
            print(f"[INFO] Existing collection deleted: {name}")
        except Exception:
            # 首次运行可能不存在旧集合，忽略即可。
            pass
    return client.get_or_create_collection(name=name)


def main() -> int:
    """主流程：加载配置 -> 读库 -> 向量化 -> 写入 Chroma。"""

    # 优先加载 backend/.env，随后再加载当前目录 .env（兼容不同启动路径）。
    backend_env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(backend_env_path)
    load_dotenv()
    config = parse_args()

    # dry-run 只验证读取与拼装流程，不强制要求 embedding key。
    if not config.dry_run and not config.embedding_api_key:
        raise ValueError("Missing environment variable: EMBEDDING_API_KEY")

    embeddings: OpenAIEmbeddings | None = None
    if not config.dry_run:
        # 创建 embedding 客户端（OpenAI 兼容接口）。
        embeddings = OpenAIEmbeddings(
            model=config.embedding_model,
            api_key=config.embedding_api_key,
            base_url=config.embedding_base_url,
            # 某些兼容服务不接受 token-array 输入，显式关闭相关行为。
            tiktoken_enabled=False,
            check_embedding_ctx_length=False,
        )

    # 创建本地持久化 Chroma 客户端并定位目标集合。
    chroma_client = chromadb.PersistentClient(path=config.chroma_dir)
    collection = get_collection(
        client=chroma_client,
        name=config.chroma_collection,
        truncate=config.truncate,
    )

    total_rows = 0
    total_upserted = 0

    # 打开 PostgreSQL 连接并按批次拉取数据。
    with psycopg.connect(config.pg_dsn) as connection:
        # 先读取真实字段，避免查询不存在的列。
        existing_columns = get_existing_columns(
            connection=connection,
            schema=config.pg_schema,
            table=config.pg_table,
        )
        if not existing_columns:
            raise ValueError(
                f"Table not found: {config.pg_schema}.{config.pg_table}. "
                "Check PG_SCHEMA / PG_TABLE."
            )
        if "id" not in existing_columns:
            raise ValueError("The source table must contain an `id` column.")

        # 仅保留数据库中真实存在的字段。
        available_content_fields = [
            field_pair for field_pair in CONTENT_FIELDS if field_pair[0] in existing_columns
        ]
        available_metadata_fields = [
            field for field in METADATA_FIELDS if field in existing_columns
        ]
        # 构造去重后的查询字段集合。
        select_columns = sorted(
            {field for field, _ in available_content_fields}
            | set(available_metadata_fields)
            | {"id"}
        )

        if not available_content_fields:
            raise ValueError(
                "None of the expected metadata fields exist in source table. "
                "Expected at least one of: "
                + ", ".join(field for field, _ in CONTENT_FIELDS)
            )

        # 生成参数化查询语句。
        select_query, params = get_select_query(
            columns=select_columns,
            schema=config.pg_schema,
            table=config.pg_table,
            count=config.count,
        )

        print(f"[INFO] Start ingest from {config.pg_schema}.{config.pg_table}")
        if config.count:
            print(f"[INFO] Row count limit: {config.count}")

        # 用字典行，便于按字段名取值。
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(select_query, params)

            # 分批读取，控制内存占用。
            while True:
                rows = cursor.fetchmany(config.batch_size)
                if not rows:
                    break

                # 组织 Chroma upsert 所需数组（必须一一对应）。
                ids: list[str] = []
                documents: list[str] = []
                metadatas: list[dict[str, Any]] = []

                for row in rows:
                    total_rows += 1
                    # 将该行数据拼成可向量化文本。
                    doc_text = build_document(row=row, available_fields=available_content_fields)
                    if not doc_text:
                        continue

                    # 每条记录必须有稳定且唯一的向量 ID。
                    row_id = normalize_value(row.get("id"))
                    if not row_id:
                        continue

                    # 向量 ID 格式：<table>:<id>
                    ids.append(f"{config.pg_table}:{row_id}")
                    documents.append(doc_text)

                    # 附加 metadata，供后续结果展示与过滤使用。
                    metadata = build_metadata(
                        row=row, available_metadata_fields=available_metadata_fields
                    )
                    metadata["source_table"] = f"{config.pg_schema}.{config.pg_table}"
                    metadatas.append(metadata)

                # 当前批次没有可写入记录时直接跳过。
                if not ids:
                    continue

                if config.dry_run:
                    # dry-run 只验证读取与拼装，不做向量化与写入。
                    total_upserted += len(ids)
                    print(
                        f"[DRY-RUN] processed={total_rows} prepared_upsert={total_upserted}"
                    )
                    continue

                if embeddings is None:
                    raise RuntimeError("Embedding client is not initialized.")

                # 生成向量并 upsert 到 Chroma。
                vectors = embed_documents_safe(embeddings=embeddings, texts=documents)
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=vectors,
                )
                total_upserted += len(ids)
                print(
                    f"[INFO] processed={total_rows} upserted={total_upserted} "
                    f"batch={len(ids)}"
                )

    # 输出最终导入统计。
    print(
        f"[DONE] source_rows={total_rows} vectorized_docs={total_upserted} "
        f"collection={config.chroma_collection}"
    )
    return 0


if __name__ == "__main__":
    try:
        # 正常执行路径。
        raise SystemExit(main())
    except KeyboardInterrupt:
        # 用户手动中断（Ctrl+C）。
        print("\n[INFO] Interrupted by user.")
        raise SystemExit(130)
    except Exception as exc:
        # 错误输出到 stderr，方便命令行与日志定位。
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
