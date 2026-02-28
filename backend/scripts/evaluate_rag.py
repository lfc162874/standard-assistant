#!/usr/bin/env python3
from __future__ import annotations

"""
RAG 回归评测脚本。

目标：
1. 批量调用 `/api/v1/chat`，评估当前检索增强问答效果。
2. 输出核心指标：Top1/TopK 命中率、引用覆盖率、clarify 比例、时延统计。
3. 生成可复跑的评测报告（JSON + Markdown + 明细 CSV）。

输入文件（CSV）建议字段：
- case_id: 用例 ID（可选）
- query: 用户问题（必填）
- expected_standard_codes: 期望标准号，多个用 `|` 或 `,` 分隔（可选）
- expected_keywords: 期望答案关键词，多个用 `|` 或 `,` 分隔（可选）
- note: 备注（可选）
"""

import argparse
import csv
import json
import math
import re
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SPLIT_PATTERN = re.compile(r"[|,;；，]\s*")


@dataclass
class EvalCase:
    """单条评测样本。"""

    case_id: str
    query: str
    expected_standard_codes: list[str]
    expected_keywords: list[str]
    note: str


@dataclass
class EvalResult:
    """单条评测结果。"""

    case_id: str
    query: str
    success: bool
    status_code: int
    latency_ms: float
    answer: str
    action: str
    retrieved_count: int
    citations: list[dict[str, Any]]
    expected_standard_codes: list[str]
    expected_keywords: list[str]
    top1_hit: bool
    topk_hit: bool
    keyword_hit: bool
    citation_non_empty: bool
    error: str
    note: str


def normalize_code(raw: str) -> str:
    """标准号归一化：去空白并转大写，便于做命中匹配。"""

    return "".join(raw.upper().split())


def split_multi(raw: str) -> list[str]:
    """按常见分隔符拆分多值字段（支持中英文逗号、分号、竖线）。"""

    text = raw.strip()
    if not text:
        return []
    return [item.strip() for item in SPLIT_PATTERN.split(text) if item.strip()]


def parse_cases(csv_path: Path, max_cases: int | None = None) -> list[EvalCase]:
    """读取 CSV 样本并转换为评测用例列表。"""

    if not csv_path.exists():
        raise FileNotFoundError(f"评测文件不存在: {csv_path}")

    cases: list[EvalCase] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if "query" not in reader.fieldnames if reader.fieldnames else []:
            raise ValueError("评测 CSV 必须包含 `query` 列")

        for idx, row in enumerate(reader, start=1):
            query = (row.get("query") or "").strip()
            if not query:
                continue

            case_id = (row.get("case_id") or "").strip() or f"case_{idx:04d}"
            expected_codes_raw = split_multi((row.get("expected_standard_codes") or "").strip())
            expected_codes = [normalize_code(item) for item in expected_codes_raw if item]
            expected_keywords = split_multi((row.get("expected_keywords") or "").strip())
            note = (row.get("note") or "").strip()

            cases.append(
                EvalCase(
                    case_id=case_id,
                    query=query,
                    expected_standard_codes=expected_codes,
                    expected_keywords=expected_keywords,
                    note=note,
                )
            )

            if max_cases is not None and len(cases) >= max_cases:
                break

    return cases


def post_chat(base_url: str, timeout: float, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """调用 `/api/v1/chat`，返回 HTTP 状态码与 JSON 响应体。"""

    url = f"{base_url.rstrip('/')}/api/v1/chat"
    request = Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
            body = json.loads(detail)
        except Exception:
            body = {"detail": str(exc)}
        return exc.code, body
    except URLError as exc:
        return 0, {"detail": f"网络错误: {exc}"}


def evaluate_case(
    case: EvalCase,
    index: int,
    base_url: str,
    timeout: float,
    user_id: str,
) -> EvalResult:
    """执行单条评测用例，并计算命中情况。"""

    payload = {
        "user_id": user_id,
        # 每条用例使用独立 session，避免 Memory 干扰评测结果。
        "session_id": f"eval_{case.case_id}_{index}",
        "query": case.query,
    }

    start = time.perf_counter()
    status_code, body = post_chat(base_url=base_url, timeout=timeout, payload=payload)
    latency_ms = (time.perf_counter() - start) * 1000

    if status_code != 200:
        return EvalResult(
            case_id=case.case_id,
            query=case.query,
            success=False,
            status_code=status_code,
            latency_ms=latency_ms,
            answer="",
            action="",
            retrieved_count=0,
            citations=[],
            expected_standard_codes=case.expected_standard_codes,
            expected_keywords=case.expected_keywords,
            top1_hit=False,
            topk_hit=False,
            keyword_hit=False,
            citation_non_empty=False,
            error=str(body.get("detail", "未知错误")),
            note=case.note,
        )

    answer = str(body.get("answer", "")).strip()
    action = str(body.get("action", "")).strip()
    data = body.get("data", {}) if isinstance(body.get("data"), dict) else {}
    retrieved_count_raw = data.get("retrieved_count", 0)
    retrieved_count = int(retrieved_count_raw) if isinstance(retrieved_count_raw, int) else 0

    raw_citations = body.get("citations", [])
    citations = raw_citations if isinstance(raw_citations, list) else []

    cited_codes = []
    for item in citations:
        if not isinstance(item, dict):
            continue
        code = normalize_code(str(item.get("standard_code", "")).strip())
        if code:
            cited_codes.append(code)

    expected_code_set = set(case.expected_standard_codes)
    top1_hit = bool(
        expected_code_set and cited_codes and cited_codes[0] in expected_code_set
    )
    topk_hit = bool(expected_code_set and set(cited_codes) & expected_code_set)

    answer_upper = answer.upper()
    keyword_hit = False
    if case.expected_keywords:
        keyword_hit = all(keyword.upper() in answer_upper for keyword in case.expected_keywords)

    return EvalResult(
        case_id=case.case_id,
        query=case.query,
        success=True,
        status_code=200,
        latency_ms=latency_ms,
        answer=answer,
        action=action,
        retrieved_count=retrieved_count,
        citations=citations,
        expected_standard_codes=case.expected_standard_codes,
        expected_keywords=case.expected_keywords,
        top1_hit=top1_hit,
        topk_hit=topk_hit,
        keyword_hit=keyword_hit,
        citation_non_empty=bool(citations),
        error="",
        note=case.note,
    )


def percentile(values: list[float], p: float) -> float:
    """计算分位数（线性插值）。"""

    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    ratio = rank - low
    return sorted_values[low] * (1 - ratio) + sorted_values[high] * ratio


def build_summary(results: list[EvalResult]) -> dict[str, Any]:
    """聚合所有用例结果，产出汇总指标。"""

    total = len(results)
    success_results = [item for item in results if item.success]
    success_count = len(success_results)
    failed_count = total - success_count

    latencies = [item.latency_ms for item in success_results]
    avg_latency_ms = statistics.mean(latencies) if latencies else 0.0
    p95_latency_ms = percentile(latencies, 0.95) if latencies else 0.0

    citation_count = sum(1 for item in success_results if item.citation_non_empty)
    clarify_count = sum(1 for item in success_results if item.action == "clarify")

    code_eval_results = [item for item in success_results if item.expected_standard_codes]
    code_eval_count = len(code_eval_results)
    top1_hit_count = sum(1 for item in code_eval_results if item.top1_hit)
    topk_hit_count = sum(1 for item in code_eval_results if item.topk_hit)

    keyword_eval_results = [item for item in success_results if item.expected_keywords]
    keyword_eval_count = len(keyword_eval_results)
    keyword_hit_count = sum(1 for item in keyword_eval_results if item.keyword_hit)

    return {
        "total_cases": total,
        "success_cases": success_count,
        "failed_cases": failed_count,
        "citation_coverage_rate": (citation_count / success_count) if success_count else 0.0,
        "clarify_rate": (clarify_count / success_count) if success_count else 0.0,
        "avg_latency_ms": avg_latency_ms,
        "p95_latency_ms": p95_latency_ms,
        "code_eval_cases": code_eval_count,
        "top1_hit_rate": (top1_hit_count / code_eval_count) if code_eval_count else 0.0,
        "topk_hit_rate": (topk_hit_count / code_eval_count) if code_eval_count else 0.0,
        "keyword_eval_cases": keyword_eval_count,
        "keyword_hit_rate": (keyword_hit_count / keyword_eval_count) if keyword_eval_count else 0.0,
    }


def write_detail_csv(output_path: Path, results: list[EvalResult]) -> None:
    """输出逐条评测明细 CSV，便于复盘错例。"""

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "case_id",
                "query",
                "success",
                "status_code",
                "latency_ms",
                "action",
                "retrieved_count",
                "citation_non_empty",
                "top1_hit",
                "topk_hit",
                "keyword_hit",
                "expected_standard_codes",
                "expected_keywords",
                "cited_standard_codes",
                "error",
                "note",
            ]
        )
        for item in results:
            cited_codes = []
            for citation in item.citations:
                if isinstance(citation, dict):
                    cited_codes.append(str(citation.get("standard_code", "")).strip())
            writer.writerow(
                [
                    item.case_id,
                    item.query,
                    item.success,
                    item.status_code,
                    f"{item.latency_ms:.2f}",
                    item.action,
                    item.retrieved_count,
                    item.citation_non_empty,
                    item.top1_hit,
                    item.topk_hit,
                    item.keyword_hit,
                    "|".join(item.expected_standard_codes),
                    "|".join(item.expected_keywords),
                    "|".join(cited_codes),
                    item.error,
                    item.note,
                ]
            )


def write_markdown_report(
    output_path: Path,
    summary: dict[str, Any],
    results: list[EvalResult],
    base_url: str,
    input_file: Path,
) -> None:
    """输出 Markdown 报告，便于直接提交到文档或 PR。"""

    failed_cases = [item for item in results if not item.success]
    miss_cases = [
        item
        for item in results
        if item.success and item.expected_standard_codes and not item.topk_hit
    ][:10]

    lines: list[str] = []
    lines.append("# RAG 评测报告")
    lines.append("")
    lines.append(f"- 评测时间：{datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- 接口地址：`{base_url}`")
    lines.append(f"- 用例文件：`{input_file}`")
    lines.append("")
    lines.append("## 汇总指标")
    lines.append("")
    lines.append(f"- 总用例数：`{summary['total_cases']}`")
    lines.append(f"- 成功数：`{summary['success_cases']}`")
    lines.append(f"- 失败数：`{summary['failed_cases']}`")
    lines.append(f"- 引用覆盖率：`{summary['citation_coverage_rate']:.2%}`")
    lines.append(f"- Clarify 比例：`{summary['clarify_rate']:.2%}`")
    lines.append(f"- 平均时延：`{summary['avg_latency_ms']:.2f} ms`")
    lines.append(f"- P95 时延：`{summary['p95_latency_ms']:.2f} ms`")
    lines.append(
        f"- Top1 命中率（标准号）：`{summary['top1_hit_rate']:.2%}` / 样本数 `{summary['code_eval_cases']}`"
    )
    lines.append(
        f"- TopK 命中率（标准号）：`{summary['topk_hit_rate']:.2%}` / 样本数 `{summary['code_eval_cases']}`"
    )
    lines.append(
        f"- 关键词命中率：`{summary['keyword_hit_rate']:.2%}` / 样本数 `{summary['keyword_eval_cases']}`"
    )
    lines.append("")
    lines.append("## 失败用例（最多 10 条）")
    lines.append("")
    if not failed_cases:
        lines.append("- 无")
    else:
        for item in failed_cases[:10]:
            lines.append(
                f"- `{item.case_id}` | status={item.status_code} | query={item.query} | error={item.error}"
            )
    lines.append("")
    lines.append("## 标准号未命中样例（最多 10 条）")
    lines.append("")
    if not miss_cases:
        lines.append("- 无")
    else:
        for item in miss_cases:
            lines.append(f"- `{item.case_id}` | query={item.query}")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="RAG 批量评测脚本")
    parser.add_argument(
        "--input",
        default="../docs/eval_questions_template.csv",
        help="评测 CSV 文件路径",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="后端服务地址（默认 http://127.0.0.1:8000）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="单请求超时秒数",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="最多评测多少条样本（可选）",
    )
    parser.add_argument(
        "--user-id",
        default="eval_user",
        help="评测请求使用的 user_id",
    )
    parser.add_argument(
        "--output-dir",
        default="./eval_reports",
        help="评测报告输出目录",
    )
    return parser.parse_args()


def main() -> int:
    """脚本入口：执行评测并输出报告文件。"""

    args = parse_args()
    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = parse_cases(csv_path=input_path, max_cases=args.max_cases)
    if not cases:
        raise ValueError("评测样本为空，请检查 CSV 文件内容")

    results: list[EvalResult] = []
    for index, case in enumerate(cases, start=1):
        result = evaluate_case(
            case=case,
            index=index,
            base_url=args.base_url,
            timeout=args.timeout,
            user_id=args.user_id,
        )
        results.append(result)
        print(
            f"[{index}/{len(cases)}] case_id={result.case_id} "
            f"status={result.status_code} latency={result.latency_ms:.2f}ms "
            f"topk_hit={result.topk_hit} citations={len(result.citations)}"
        )

    summary = build_summary(results=results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report_json_path = output_dir / f"rag_eval_report_{timestamp}.json"
    report_md_path = output_dir / f"rag_eval_report_{timestamp}.md"
    detail_csv_path = output_dir / f"rag_eval_detail_{timestamp}.csv"

    report_payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "base_url": args.base_url,
            "input_file": str(input_path),
            "output_dir": str(output_dir),
        },
        "summary": summary,
        "results": [item.__dict__ for item in results],
    }
    report_json_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown_report(
        output_path=report_md_path,
        summary=summary,
        results=results,
        base_url=args.base_url,
        input_file=input_path,
    )
    write_detail_csv(output_path=detail_csv_path, results=results)

    print("\n[评测完成]")
    print(f"- JSON 报告: {report_json_path}")
    print(f"- Markdown 报告: {report_md_path}")
    print(f"- 明细 CSV: {detail_csv_path}")
    print(
        "- 核心指标: "
        f"Top1={summary['top1_hit_rate']:.2%}, "
        f"TopK={summary['topk_hit_rate']:.2%}, "
        f"引用覆盖率={summary['citation_coverage_rate']:.2%}, "
        f"P95={summary['p95_latency_ms']:.2f}ms"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断。")
        raise SystemExit(130)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
