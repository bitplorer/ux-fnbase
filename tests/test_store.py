"""Core store invariants."""

from __future__ import annotations

import pytest

from ux_fnbase import (
    NestedTransactionError,
    SchemaViolationError,
    Store,
    TableSchema,
    literal,
    string,
)
from playground.demo import create_demo_store


def test_seed_and_board():
    store = create_demo_store()
    board = store.run_query("board")
    assert sum(len(board[k]) for k in ("backlog", "doing", "done")) == 3
    stats = store.run_query("stats")
    assert stats["total"] == 3
    store.close()


def test_mutation_advances_generation():
    store = create_demo_store()
    g0 = store.generation
    store.run_mutation("add_task", {"title": "x", "author": "north"})
    assert store.generation == g0 + 1
    store.close()


def test_thrown_mutation_does_not_advance():
    store = create_demo_store()
    g0 = store.generation

    @store.mutation
    def boom(ctx):
        ctx.db.table("tasks").insert(
            {"title": "temp", "status": "backlog", "author": "n", "note": ""}
        )
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        store.run_mutation("boom")
    assert store.generation == g0
    assert store.run_query("stats")["total"] == 3
    store.close()


def test_nested_mutation_from_subscriber_fails_closed():
    store = create_demo_store()
    nested: list = []

    def cb(result, meta):
        try:
            store.run_mutation("add_task", {"title": "from notify", "author": "north"})
        except NestedTransactionError as exc:
            nested.append(exc)

    store.subscribe("stats", None, cb)
    nested.clear()  # clear immediate idle callback
    store.run_mutation("add_task", {"title": "trigger", "author": "north"})
    assert nested, "notify-phase mutation must fail closed"
    store.close()


def test_index_invalidation_precise():
    store = create_demo_store()
    hits: list = []

    def cb(result, meta):
        hits.append(len(result))

    store.subscribe("by_status", {"status": "done"}, cb)
    baseline = len(hits)
    store.run_mutation("add_task", {"title": "stays backlog", "author": "south"})
    assert len(hits) == baseline
    store.close()


def test_schema_rejects_bad_status():
    store = create_demo_store()
    doc = store.snapshot_documents("tasks")[0]
    with pytest.raises(SchemaViolationError):
        store.run_mutation("move_task", {"id": doc["_id"], "status": "invalid"})
    store.close()


def test_two_subscribers_see_one_mutation():
    store = create_demo_store()
    a: list = []
    b: list = []
    store.subscribe("board", None, lambda r, m: a.append(len(r["backlog"])))
    store.subscribe("board", None, lambda r, m: b.append(len(r["backlog"])))
    store.run_mutation("add_task", {"title": "shared", "author": "north"})
    assert a[-1] == b[-1] == 2
    store.close()
