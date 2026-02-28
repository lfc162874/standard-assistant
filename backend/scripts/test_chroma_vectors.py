#!/usr/bin/env python3
from __future__ import annotations

"""
Chroma vector verification script.

Purpose:
1) Check if target collection exists and contains vectors.
2) Query by a natural-language question and print TopK hits.
3) Help verify whether ingest quality is acceptable before wiring RAG.
"""

import argparse
import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


def parse_args() -> argparse.Namespace:
    """Parse CLI parameters for simple vector search verification."""

    parser = argparse.ArgumentParser(
        description="Query local Chroma collection and print TopK vector hits."
    )
    parser.add_argument(
        "--query",
        required=True,
        help='Question text, for example: --query "口罩相关标准有哪些？"',
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("RAG_TOP_K", "5").strip()),
        help="How many results to return (default: 5).",
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("CHROMA_COLLECTION", "standards_meta_v1").strip(),
        help="Chroma collection name.",
    )
    parser.add_argument(
        "--chroma-dir",
        default=os.getenv("CHROMA_PERSIST_DIR", "./chroma_data").strip(),
        help="Local Chroma persist directory.",
    )
    return parser.parse_args()


def main() -> int:
    """Load config, build query embedding, search Chroma, and print results."""

    # Load backend/.env first for stable behavior regardless of current cwd.
    backend_env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(backend_env_path)
    load_dotenv()

    args = parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")

    embedding_api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
    if not embedding_api_key:
        raise ValueError("Missing environment variable: EMBEDDING_API_KEY")

    embedding_base_url = os.getenv(
        "EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ).strip()
    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-v4").strip()

    # Build query embedding client.
    embeddings = OpenAIEmbeddings(
        model=embedding_model,
        api_key=embedding_api_key,
        base_url=embedding_base_url,
        # Keep provider-compatible text-only mode.
        tiktoken_enabled=False,
        check_embedding_ctx_length=False,
    )

    # Connect local Chroma and load collection.
    client = chromadb.PersistentClient(path=args.chroma_dir)
    collection = client.get_collection(name=args.collection)

    # Quick collection count check.
    total = collection.count()
    print(f"[INFO] Collection: {args.collection}")
    print(f"[INFO] Vector count: {total}")

    if total == 0:
        print("[WARN] Collection is empty. Run ingest script first.")
        return 0

    # Compute embedding for the user query.
    query_vector = embeddings.embed_query(args.query)

    # Execute vector search.
    result = collection.query(
        query_embeddings=[query_vector],
        n_results=args.top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    print(f"[INFO] Query: {args.query}")
    print(f"[INFO] TopK: {args.top_k}")
    print("-" * 80)

    # Print readable TopK results.
    for idx, doc_id in enumerate(ids, start=1):
        meta = metas[idx - 1] if idx - 1 < len(metas) else {}
        doc = docs[idx - 1] if idx - 1 < len(docs) else ""
        distance = distances[idx - 1] if idx - 1 < len(distances) else None

        print(f"[{idx}] id={doc_id}")
        print(f"    distance={distance}")
        print(f"    a100={meta.get('a100', '')}")
        print(f"    a298={meta.get('a298', '')}")
        print(f"    a101={meta.get('a101', '')}")
        print(f"    a825cn={meta.get('a825cn', '')}")
        print(f"    a826cn={meta.get('a826cn', '')}")

        # Show first 200 chars to keep output compact.
        preview = (doc or "").replace("\n", " ")
        if len(preview) > 200:
            preview = preview[:200] + "..."
        print(f"    doc_preview={preview}")
        print("-" * 80)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
