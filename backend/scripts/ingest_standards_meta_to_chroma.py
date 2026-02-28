#!/usr/bin/env python3
from __future__ import annotations

"""
PostgreSQL metadata -> Embedding -> Chroma ingest script.

What this script does:
1) Read rows from table `drms_standard_middle_sync`.
2) Build one metadata document per row from selected fields.
3) Call embedding model (text-embedding-v4) to get vectors.
4) Upsert vectors/documents/metadata into local Chroma collection.

Notes:
- Does NOT rely on `is_deleted` or `update_time`.
- Supports `--count` so you can ingest a subset (e.g. 10000 rows) for testing.
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


# Fields used to build vectorized text content.
# Left value = source column name in PostgreSQL
# Right value = human-readable label included in the document text
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
]

# Fields copied into Chroma metadata for filtering / display / tracing.
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
]


@dataclass
class RuntimeConfig:
    """Runtime config assembled from CLI args + environment variables."""

    # PostgreSQL connection and table location
    pg_dsn: str
    pg_schema: str
    pg_table: str

    # Chroma storage location and collection name
    chroma_dir: str
    chroma_collection: str

    # Embedding provider settings
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str

    # Ingest behavior
    batch_size: int
    count: int | None
    truncate: bool
    dry_run: bool


def build_pg_dsn() -> str:
    """Build psycopg DSN string from `PG_DSN` or split PG_* env variables."""

    # Highest priority: explicit DSN (single variable).
    dsn = os.getenv("PG_DSN", "").strip()
    if dsn:
        return dsn

    # Fallback: compose DSN from host/port/user/password/database.
    host = os.getenv("PG_HOST", "localhost").strip()
    port = os.getenv("PG_PORT", "5432").strip()
    user = os.getenv("PG_USER", "postgres").strip()
    password = os.getenv("PG_PASSWORD", "123456").strip()
    database = os.getenv("PG_DATABASE", "postgres").strip()
    return (
        f"host={host} port={port} dbname={database} user={user} password={password}"
    )


def parse_args() -> RuntimeConfig:
    """Parse CLI arguments and build final runtime configuration."""

    parser = argparse.ArgumentParser(
        description=(
            "Read standard metadata from PostgreSQL, build embeddings with "
            "text-embedding-v4, and upsert into local Chroma."
        )
    )

    # Support both INGEST_COUNT (new) and INGEST_LIMIT (legacy alias).
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
        # Keep old CLI name for backward compatibility, but hide from help output.
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

    # Basic argument guards to fail fast with clear errors.
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
    """Normalize DB values to clean strings used by documents/metadata."""

    # None means empty.
    if value is None:
        return ""
    # Convert datetime to readable string.
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    # Default conversion for all other types.
    return str(value).strip()


def get_existing_columns(
    connection: psycopg.Connection[Any], schema: str, table: str
) -> set[str]:
    """Read existing column names from information_schema for safety checks."""

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
    """Build one text document from a row using configured content fields."""

    lines: list[str] = []
    for field, label in available_fields:
        value = normalize_value(row.get(field))
        # Skip empty values to keep text concise.
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def build_metadata(row: dict[str, Any], available_metadata_fields: list[str]) -> dict[str, Any]:
    """Build Chroma metadata payload for a row."""

    metadata: dict[str, Any] = {}
    for field in available_metadata_fields:
        value = normalize_value(row.get(field))
        # Keep metadata compact: do not store empty values.
        if value:
            metadata[field] = value
    return metadata


def embed_documents_safe(embeddings: OpenAIEmbeddings, texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings with provider compatibility fallback.

    Why:
    - Some OpenAI-compatible services reject certain batch payload formats and return:
      InvalidParameter / input.contents.
    Strategy:
    - Try `embed_documents` first (faster, batched).
    - If provider rejects payload format, fallback to `embed_query` per text.
    """

    # Enforce list[str] to avoid accidental non-string payload types.
    normalized_texts = [text if isinstance(text, str) else str(text) for text in texts]
    try:
        # Preferred path: batch embedding for better throughput.
        return embeddings.embed_documents(normalized_texts)
    except Exception as exc:
        error_message = str(exc)
        # If it's not the known provider compatibility error, re-raise directly.
        if "input.contents" not in error_message and "InvalidParameter" not in error_message:
            raise

        print(
            "[WARN] Batch embedding request failed with InvalidParameter. "
            "Fallback to single-text embedding mode."
        )
        vectors: list[list[float]] = []
        for text in normalized_texts:
            # Compatibility path: embed one text at a time.
            vectors.append(embeddings.embed_query(text))
        return vectors


def get_select_query(
    columns: list[str],
    schema: str,
    table: str,
    count: int | None,
) -> tuple[sql.Composed, list[Any]]:
    """Build SELECT query safely via psycopg sql.Identifier."""

    # Select only needed columns to reduce I/O and memory overhead.
    query = sql.SQL("SELECT {fields} FROM {table}").format(
        fields=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        table=sql.Identifier(schema, table),
    )
    params: list[Any] = []

    # Stable order for deterministic ingest.
    query += sql.SQL(" ORDER BY {column} ASC").format(column=sql.Identifier("id"))

    # Optional row cap for controlled test imports.
    if count:
        query += sql.SQL(" LIMIT %s")
        params.append(count)

    return query, params


def get_collection(client: chromadb.PersistentClient, name: str, truncate: bool):
    """Get or create Chroma collection; optionally delete previous one first."""

    if truncate:
        try:
            client.delete_collection(name)
            print(f"[INFO] Existing collection deleted: {name}")
        except Exception:
            # Collection may not exist on first run.
            pass
    return client.get_or_create_collection(name=name)


def main() -> int:
    """Main workflow: load config, read DB rows, embed, upsert to Chroma."""

    # Load env from backend/.env first, then fallback to current working dir .env.
    backend_env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(backend_env_path)
    load_dotenv()
    config = parse_args()

    # In dry-run mode, embedding key is not required.
    if not config.dry_run and not config.embedding_api_key:
        raise ValueError("Missing environment variable: EMBEDDING_API_KEY")

    embeddings: OpenAIEmbeddings | None = None
    if not config.dry_run:
        # Create embedding client (OpenAI-compatible API).
        embeddings = OpenAIEmbeddings(
            model=config.embedding_model,
            api_key=config.embedding_api_key,
            base_url=config.embedding_base_url,
            # For some OpenAI-compatible providers, token-array input is rejected.
            tiktoken_enabled=False,
            check_embedding_ctx_length=False,
        )

    # Create local persistent Chroma client and target collection.
    chroma_client = chromadb.PersistentClient(path=config.chroma_dir)
    collection = get_collection(
        client=chroma_client,
        name=config.chroma_collection,
        truncate=config.truncate,
    )

    total_rows = 0
    total_upserted = 0

    # Open PostgreSQL connection and stream rows in batches.
    with psycopg.connect(config.pg_dsn) as connection:
        # Read real table columns first to avoid selecting non-existent columns.
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

        # Keep only fields that actually exist in this DB table.
        available_content_fields = [
            field_pair for field_pair in CONTENT_FIELDS if field_pair[0] in existing_columns
        ]
        available_metadata_fields = [
            field for field in METADATA_FIELDS if field in existing_columns
        ]
        # Build deduplicated select column list.
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

        # Build parameterized query.
        select_query, params = get_select_query(
            columns=select_columns,
            schema=config.pg_schema,
            table=config.pg_table,
            count=config.count,
        )

        print(f"[INFO] Start ingest from {config.pg_schema}.{config.pg_table}")
        if config.count:
            print(f"[INFO] Row count limit: {config.count}")

        # Use dict rows so columns are accessible by name.
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(select_query, params)

            # Fetch data chunk by chunk to control memory usage.
            while True:
                rows = cursor.fetchmany(config.batch_size)
                if not rows:
                    break

                # Chroma upsert payload arrays (same order/length required).
                ids: list[str] = []
                documents: list[str] = []
                metadatas: list[dict[str, Any]] = []

                for row in rows:
                    total_rows += 1
                    # Build one text document from selected metadata fields.
                    doc_text = build_document(row=row, available_fields=available_content_fields)
                    if not doc_text:
                        continue

                    # Ensure every vector record has deterministic unique id.
                    row_id = normalize_value(row.get("id"))
                    if not row_id:
                        continue

                    # Record id format: <table>:<id>
                    ids.append(f"{config.pg_table}:{row_id}")
                    documents.append(doc_text)

                    # Attach original metadata fields for later display/filtering.
                    metadata = build_metadata(
                        row=row, available_metadata_fields=available_metadata_fields
                    )
                    metadata["source_table"] = f"{config.pg_schema}.{config.pg_table}"
                    metadatas.append(metadata)

                # If this chunk has no valid documents, skip it.
                if not ids:
                    continue

                if config.dry_run:
                    # Dry-run only validates read/build logic, no embedding/no upsert.
                    total_upserted += len(ids)
                    print(
                        f"[DRY-RUN] processed={total_rows} prepared_upsert={total_upserted}"
                    )
                    continue

                if embeddings is None:
                    raise RuntimeError("Embedding client is not initialized.")

                # Generate embeddings and upsert into Chroma.
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

    # Final summary.
    print(
        f"[DONE] source_rows={total_rows} vectorized_docs={total_upserted} "
        f"collection={config.chroma_collection}"
    )
    return 0


if __name__ == "__main__":
    try:
        # Normal exit path.
        raise SystemExit(main())
    except KeyboardInterrupt:
        # User interrupted with Ctrl+C.
        print("\n[INFO] Interrupted by user.")
        raise SystemExit(130)
    except Exception as exc:
        # Print concise error to stderr for shell visibility.
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
