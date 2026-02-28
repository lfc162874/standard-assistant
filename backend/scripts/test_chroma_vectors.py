#!/usr/bin/env python3
from __future__ import annotations

"""
Chroma 向量检索验证脚本。

用途：
1. 检查目标集合是否存在且已有向量数据。
2. 输入自然语言问题，查看 TopK 召回结果。
3. 在接入 RAG 之前先验证向量化质量是否可用。
"""

import argparse
import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


def parse_args() -> argparse.Namespace:
    """解析命令行参数（用于快速向量检索验证）。"""

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
        help="返回结果条数（默认 5）。",
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("CHROMA_COLLECTION", "standards_meta_v1").strip(),
        help="Chroma 集合名称。",
    )
    parser.add_argument(
        "--chroma-dir",
        default=os.getenv("CHROMA_PERSIST_DIR", "./chroma_data").strip(),
        help="本地 Chroma 持久化目录。",
    )
    return parser.parse_args()


def main() -> int:
    """主流程：加载配置、计算查询向量、检索 Chroma 并打印结果。"""

    # 优先加载 backend/.env，避免不同启动目录导致配置读取不一致。
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

    # 构建查询向量客户端。
    embeddings = OpenAIEmbeddings(
        model=embedding_model,
        api_key=embedding_api_key,
        base_url=embedding_base_url,
        # 保持“纯文本输入”模式，提升兼容 OpenAI 兼容接口的稳定性。
        tiktoken_enabled=False,
        check_embedding_ctx_length=False,
    )

    # 连接本地 Chroma 并加载目标集合。
    client = chromadb.PersistentClient(path=args.chroma_dir)
    collection = client.get_collection(name=args.collection)

    # 先看集合总向量数，判断是否已成功导入。
    total = collection.count()
    print(f"[INFO] Collection: {args.collection}")
    print(f"[INFO] Vector count: {total}")

    if total == 0:
        print("[WARN] 集合为空，请先执行向量导入脚本。")
        return 0

    # 计算用户问题的查询向量。
    query_vector = embeddings.embed_query(args.query)

    # 执行向量检索。
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

    # 逐条打印 TopK 结果，便于人工判断召回质量。
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
        print(f"    a330={meta.get('a330', '')}")

        # 只展示文档预览前 200 字，避免输出过长。
        preview = (doc or "").replace("\n", " ")
        if len(preview) > 200:
            preview = preview[:200] + "..."
        print(f"    doc_preview={preview}")
        print("-" * 80)

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
        # 错误输出到 stderr，方便排查。
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
