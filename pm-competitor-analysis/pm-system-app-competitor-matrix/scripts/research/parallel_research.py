#!/usr/bin/env python3
"""与检索供应商无关的 Research Unit 分批/并行 Worker 调度器。

模式：
- plan：生成 Query Set 并输出 JSONL 研究计划，不访问网络。
- run：并发执行用户提供的 Worker 命令。每个 Research Plan 通过 stdin 发送 JSON，
       Worker 需通过 stdout 返回 JSON。

脚本刻意不绑定任何搜索供应商，也不内置 API Key。
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import shlex
import subprocess
from typing import Dict, Iterable, List

from query_builder import build_queries


def read_jsonl(path: str) -> List[Dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"第 {line_no} 行不是合法 JSONL：{e}")
    return rows


def enrich(unit: Dict) -> Dict:
    out = dict(unit)
    out["query_sets"] = build_queries(unit)
    return out


def run_worker(plan: Dict, command: str, timeout: int) -> Dict:
    proc = subprocess.run(
        shlex.split(command),
        input=json.dumps(plan, ensure_ascii=False),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    result = {
        "unit_id": plan.get("unit_id"),
        "returncode": proc.returncode,
        "stderr": proc.stderr.strip() or None,
    }
    if proc.stdout.strip():
        try:
            result["worker_result"] = json.loads(proc.stdout)
        except json.JSONDecodeError:
            result["worker_result_raw"] = proc.stdout.strip()
    return result


def write_jsonl(path: str, rows: Iterable[Dict]):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    p = argparse.ArgumentParser(description="生成或并发执行竞品证据检索计划")
    p.add_argument("--input", required=True, help="ResearchUnit JSONL 输入文件")
    p.add_argument("--output", required=True, help="输出 JSONL 文件")
    p.add_argument("--mode", choices=["plan", "run"], default="plan", help="plan=只生成计划；run=并发执行 Worker")
    p.add_argument("--worker-command", help="run 模式必填。Worker 从 stdin 读取 JSON，并向 stdout 返回 JSON。")
    p.add_argument("--max-concurrency", type=int, default=8, help="最大并发数")
    p.add_argument("--timeout", type=int, default=120, help="单个 Worker 超时时间（秒）")
    args = p.parse_args()

    units = read_jsonl(args.input)
    plans = [enrich(u) for u in units]

    if args.mode == "plan":
        write_jsonl(args.output, plans)
        return

    if not args.worker_command:
        raise SystemExit("run 模式必须提供 --worker-command")

    results: List[Dict] = []
    with cf.ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as ex:
        futures = [ex.submit(run_worker, plan, args.worker_command, args.timeout) for plan in plans]
        for fut in cf.as_completed(futures):
            results.append(fut.result())

    # 保持稳定顺序，便于下游做 diff 或重复运行对比。
    results.sort(key=lambda x: str(x.get("unit_id", "")))
    write_jsonl(args.output, results)


if __name__ == "__main__":
    main()
