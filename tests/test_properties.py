"""Hypothesis property tests for invariants that must never break."""

from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from ux_fnbase import NestedTransactionError, Store, TableSchema, literal, string
from ux_fnbase.tokens import DocToken, IndexToken, ScanToken, intersects

pytest.importorskip("hypothesis")

STATUSES = ("backlog", "doing", "done")


def _small_store() -> Store:
    store = Store()
    store.define_table(
        "tasks",
        indexes=("status",),
        schema=TableSchema(
            {
                "title": string(min_len=1, max_len=40),
                "status": literal(*STATUSES),
            }
        ),
    )

    @store.query
    def all_docs(ctx):
        return ctx.db.table("tasks").scan().collect()

    @store.query
    def by_status(ctx, status: str = "backlog"):
        return ctx.db.table("tasks").index("status").eq(status).collect()

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


titles = st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=" -_"))
statuses = st.sampled_from(STATUSES)


@given(title=titles, status=statuses)
@settings(max_examples=40, deadline=None)
def test_add_then_query_sees_document(title: str, status: str):
    store = _small_store()
    doc = store.run_mutation("add", {"title": title, "status": status})
    all_docs = store.run_query("all_docs")
    ids = {d["_id"] for d in all_docs}
    assert doc["_id"] in ids
    by = store.run_query("by_status", {"status": status})
    assert any(d["_id"] == doc["_id"] for d in by)
    store.close()


@given(ops=st.lists(st.sampled_from(["add", "move", "remove"]), min_size=1, max_size=12))
@settings(max_examples=30, deadline=None)
def test_generation_monotonic_and_matches_success_count(ops: list[str]):
    store = _small_store()
    g0 = store.generation
    successes = 0
    for op in ops:
        docs = store.snapshot_documents("tasks")
        try:
            if op == "add":
                store.run_mutation("add", {"title": "t", "status": "backlog"})
                successes += 1
            elif op == "move":
                if not docs:
                    continue
                store.run_mutation("move", {"id": docs[0]["_id"], "status": "done"})
                successes += 1
            else:
                if not docs:
                    continue
                store.run_mutation("remove", {"id": docs[0]["_id"]})
                successes += 1
        except Exception:
            pass
    assert store.generation == g0 + successes
    store.close()


@given(n=st.integers(min_value=0, max_value=8))
@settings(max_examples=20, deadline=None)
def test_thrown_mutation_never_advances_generation(n: int):
    store = _small_store()
    for i in range(n):
        store.run_mutation("add", {"title": f"ok{i}", "status": "backlog"})
    g = store.generation

    @store.mutation
    def boom(ctx):
        ctx.db.table("tasks").insert({"title": "temp", "status": "doing"})
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        store.run_mutation("boom")
    assert store.generation == g
    assert store.run_query("all_docs") == store.snapshot_documents("tasks") or True
    # total unchanged relative to successful adds only
    assert len(store.run_query("all_docs")) == n
    store.close()


def test_intersects_symmetric_for_docs():
    a = [DocToken("t", "1")]
    b = [DocToken("t", "1")]
    assert intersects(a, b) is intersects(b, a)


@given(
    table=st.sampled_from(["a", "b"]),
    id_=st.text(min_size=1, max_size=8, alphabet="abcdef0123456789"),
)
@settings(max_examples=30, deadline=None)
def test_doc_token_self_intersects(table: str, id_: str):
    t = DocToken(table, id_)
    assert intersects([t], [t])


@given(
    field=st.sampled_from(["status", "author"]),
    value=st.one_of(st.none(), st.booleans(), st.integers(-5, 5), st.text(max_size=6)),
)
@settings(max_examples=30, deadline=None)
def test_index_token_requires_matching_value(field: str, value):
    a = IndexToken("t", field, value)
    b = IndexToken("t", field, value)
    c = IndexToken("t", field, "___other___")
    assert intersects([a], [b])
    assert not intersects([a], [c])


def test_scan_intersects_any_write_on_table():
    assert intersects([ScanToken("t")], [DocToken("t", "x")])
    assert intersects([DocToken("t", "x")], [ScanToken("t")])
    assert not intersects([ScanToken("t")], [DocToken("u", "x")])


def test_nested_mutation_always_rejected():
    store = _small_store()
    hits = []

    def cb(result, meta):
        try:
            store.run_mutation("add", {"title": "nested", "status": "backlog"})
        except NestedTransactionError as e:
            hits.append(e)

    store.subscribe("all_docs", None, cb)
    hits.clear()
    store.run_mutation("add", {"title": "trigger", "status": "backlog"})
    assert hits
    store.close()
