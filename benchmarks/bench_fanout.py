#!/usr/bin/env python3
"""Subscription fanout micro-benchmark.

Reports formal numbers for this machine: mutation latency with N subscribers
on a scan query, and notify delivery cost.

Usage
-----
::

    PYTHONPATH=src:. python benchmarks/bench_fanout.py
    PYTHONPATH=src:. python benchmarks/bench_fanout.py --subscribers 50 --mutations 100
"""

from __future__ import annotations

import argparse
import statistics
import time

from ux_fnbase import Store, TableSchema, string


def build_store(n_subs: int) -> tuple[Store, list[int]]:
    store = Store()
    store.define_table(
        "items",
        schema=TableSchema({"title": string(min_len=1, max_len=40)}),
    )

    @store.query
    def all_items(ctx):
        return ctx.db.table("items").scan().collect()

    @store.mutation
    def add(ctx, title: str):
        return ctx.db.table("items").insert({"title": title})

    deliveries = [0]

    def cb(result, meta):
        deliveries[0] += 1

    for _ in range(n_subs):
        store.subscribe("all_items", None, cb)
    # each subscribe fires immediately once
    deliveries[0] = 0
    return store, deliveries


def main() -> None:
    parser = argparse.ArgumentParser(description="ux-fnbase subscription fanout benchmark")
    parser.add_argument("--subscribers", type=int, default=25)
    parser.add_argument("--mutations", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    args = parser.parse_args()

    store, deliveries = build_store(args.subscribers)
    for i in range(args.warmup):
        store.run_mutation("add", {"title": f"warm{i}"})
    deliveries[0] = 0

    samples_ms: list[float] = []
    for i in range(args.mutations):
        t0 = time.perf_counter()
        store.run_mutation("add", {"title": f"m{i}"})
        samples_ms.append((time.perf_counter() - t0) * 1000.0)

    store.close()

    def pct(xs: list[float], p: float) -> float:
        if not xs:
            return 0.0
        ordered = sorted(xs)
        idx = min(len(ordered) - 1, max(0, int(round((p / 100.0) * (len(ordered) - 1)))))
        return ordered[idx]

    print("ux-fnbase subscription fanout benchmark")
    print(f"  subscribers     : {args.subscribers}")
    print(f"  mutations       : {args.mutations}")
    print(f"  warmup          : {args.warmup}")
    print(f"  deliveries      : {deliveries[0]} (expect {args.mutations * args.subscribers})")
    print(f"  mutation p50_ms : {pct(samples_ms, 50):.3f}")
    print(f"  mutation p95_ms : {pct(samples_ms, 95):.3f}")
    print(f"  mutation p99_ms : {pct(samples_ms, 99):.3f}")
    print(f"  mutation mean_ms: {statistics.fmean(samples_ms):.3f}")
    print(f"  mutation max_ms : {max(samples_ms):.3f}")
    if deliveries[0] != args.mutations * args.subscribers:
        raise SystemExit("delivery count mismatch — fanout invariant broken")


if __name__ == "__main__":
    main()
