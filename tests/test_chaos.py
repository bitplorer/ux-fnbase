"""Chaos: random mutations under concurrent readers; invariants hold."""

from __future__ import annotations

import random
import threading

from ux_fnbase import Store, TableSchema, literal, string


def _store() -> Store:
    store = Store()
    store.define_table(
        "tasks",
        indexes=("status",),
        schema=TableSchema(
            {
                "title": string(min_len=1, max_len=40),
                "status": literal("backlog", "doing", "done"),
            }
        ),
    )

    @store.query
    def total(ctx):
        return len(ctx.db.table("tasks").scan().collect())

    @store.mutation
    def add(ctx, title: str, status: str = "backlog"):
        return ctx.db.table("tasks").insert({"title": title, "status": status})

    @store.mutation
    def move(ctx, id: str, status: str):
        return ctx.db.table("tasks").patch(id, {"status": status})

    @store.mutation
    def remove(ctx, id: str):
        ctx.db.table("tasks").delete(id)
        return True

    return store


def test_chaos_random_ops_generation_equals_successes():
    rng = random.Random(42)
    store = _store()
    successes = 0
    for i in range(80):
        docs = store.snapshot_documents("tasks")
        op = rng.choice(["add", "add", "move", "remove", "query"])
        try:
            if op == "add":
                store.run_mutation(
                    "add",
                    {
                        "title": f"t{i}",
                        "status": rng.choice(["backlog", "doing", "done"]),
                    },
                )
                successes += 1
            elif op == "move" and docs:
                store.run_mutation(
                    "move",
                    {
                        "id": rng.choice(docs)["_id"],
                        "status": rng.choice(["backlog", "doing", "done"]),
                    },
                )
                successes += 1
            elif op == "remove" and docs:
                store.run_mutation("remove", {"id": rng.choice(docs)["_id"]})
                successes += 1
            else:
                store.run_query("total")
        except Exception:
            pass
    assert store.generation == successes
    assert store.run_query("total") == len(store.snapshot_documents("tasks"))
    store.close()


def test_concurrent_readers_during_writes():
    store = _store()
    for i in range(5):
        store.run_mutation("add", {"title": f"seed{i}", "status": "backlog"})

    errors: list[BaseException] = []
    stop = threading.Event()

    def reader():
        try:
            while not stop.is_set():
                n = store.run_query("total")
                assert isinstance(n, int)
                assert n >= 0
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    try:
        for i in range(40):
            store.run_mutation("add", {"title": f"w{i}", "status": "doing"})
            docs = store.snapshot_documents("tasks")
            if docs:
                store.run_mutation(
                    "move",
                    {"id": docs[0]["_id"], "status": "done"},
                )
    finally:
        stop.set()
        for t in threads:
            t.join(timeout=2)
    assert not errors
    store.close()


def test_many_subscribers_see_consistent_totals():
    store = _store()
    seen: list[list[int]] = [[] for _ in range(5)]

    for i, bucket in enumerate(seen):
        def make_cb(b=bucket):
            def cb(result, meta):
                b.append(int(result))

            return cb

        store.subscribe("total", None, make_cb())

    for i in range(10):
        store.run_mutation("add", {"title": f"s{i}", "status": "backlog"})

    # After each successful add, every subscriber's last value should match store
    final = store.run_query("total")
    for bucket in seen:
        assert bucket[-1] == final
    store.close()
