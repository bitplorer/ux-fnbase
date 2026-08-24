# ux-fnbase — snippets

> **Diátaxis:** how-to · copy-paste patterns from the public API (`__all__` / CLI).
> Map: see this package `docs/INDEX.md`.

Function database. Queries record a read-set. Mutations emit a write-set. Subscriptions re-run only on intersection.

Every block is meant to run (or to be the exact fragment you drop into a running app). Names are public exports. If code and this page disagree, **code wins**.

## Contents

- [Install (stdlib core)](#fn-install)
- [Store, schema, query, mutation, subscribe](#fn-store)
- [Explain a query (read-set + generation)](#fn-explain)
- [Durable file backend (atomic replace)](#fn-durable)
- [Fail-closed errors](#fn-errors)
- [get() and equality indexes](#fn-get-index)
- [Optional asyncio wrappers](#fn-asyncio)

## Install

### Install (stdlib core)

<a id="fn-install"></a>

Core has zero third-party dependencies. Python ≥ 3.11.

```bash
# from the repository
pip install -e .
pip install -e ".[dev]"          # pytest, hypothesis
export PYTHONPATH=src:.
python -c "from ux_fnbase import Store; print(Store)"
```

## Core usage

### Store, schema, query, mutation, subscribe

<a id="fn-store"></a>

Queries only read via ctx.db. Mutations only write via insert/patch/delete. subscribe re-runs when read-set ∩ write-set is non-empty.

```python
from ux_fnbase import Store, TableSchema, string, literal

store = Store()
store.define_table(
    "tasks",
    indexes=("status",),
    schema=TableSchema({
        "title": string(min_len=1, max_len=80),
        "status": literal("backlog", "doing", "done"),
    }),
)

@store.query
def board(ctx):
    return ctx.db.table("tasks").scan().collect()

@store.query
def by_status(ctx, status: str):
    return ctx.db.table("tasks").index("status").eq(status).collect()

@store.mutation
def add(ctx, title: str):
    return ctx.db.table("tasks").insert({"title": title, "status": "backlog"})

@store.mutation
def complete(ctx, doc_id: str):
    return ctx.db.table("tasks").patch(doc_id, {"status": "done"})

@store.mutation
def drop(ctx, doc_id: str):
    ctx.db.table("tasks").delete(doc_id)

row = store.run_mutation("add", {"title": "Ship docs"})
print(store.run_query("board"))
print(store.run_query("by_status", {"status": "backlog"}))
store.run_mutation("complete", {"doc_id": row["_id"]})

def on_change(result, meta):
    print("generation", meta.generation, "n", len(result))

unsub = store.subscribe("board", None, on_change)
store.run_mutation("add", {"title": "Live"})
unsub()
store.close()
```

### Explain a query (read-set + generation)

<a id="fn-explain"></a>

explain() is the debugging door. stats()/journal() are operator facts, not a UI API.

```python
info = store.explain("board")
print(info["generation"], info["elapsed_ms"], info["read_set"])
print(store.stats())
print(store.journal()[-1])
print(store.snapshot_documents("tasks"))
```

### Durable file backend (atomic replace)

<a id="fn-durable"></a>

Partial disk writes raise DurabilityError and leave the in-memory store unchanged.

```python
from ux_fnbase import Store, AtomicJsonBackend

backend = AtomicJsonBackend("/tmp/ux-fnbase-board.json")
store = Store(backend=backend)
# define_table / query / mutation as usual
# commit: persist-before-publish; durability failure rolls back pre-images
```

## Fail closed

### Fail-closed errors

<a id="fn-errors"></a>

Thrown mutations do not advance generation. Notify-phase writes raise NestedTransactionError.

```python
from ux_fnbase import (
    NestedTransactionError, PhaseError, SchemaViolationError,
    FunctionNotFoundError, LimitExceededError,
)

# 1) Schema
try:
    store.run_mutation("add", {"title": ""})  # min_len=1
except SchemaViolationError as exc:
    print("schema", exc)

# 2) Nested mutation from a subscriber is illegal
def bad(result, meta):
    store.run_mutation("add", {"title": "nested"})  # raises NestedTransactionError

unsub = store.subscribe("board", None, bad)
try:
    store.run_mutation("add", {"title": "trigger"})
except NestedTransactionError:
    print("nested rejected")
unsub()

# 3) Unknown function
try:
    store.run_query("nope")
except FunctionNotFoundError:
    print("missing")
```

## Core usage

### get() and equality indexes

<a id="fn-get-index"></a>

index(field).eq(value) only works for fields listed in define_table(..., indexes=(...)). Unindexed filters are table scans.

```python
@store.query
def one(ctx, doc_id: str):
    return ctx.db.table("tasks").get(doc_id)

@store.query
def doing(ctx):
    return ctx.db.table("tasks").index("status").eq("doing").collect()

print(store.run_query("one", {"doc_id": row["_id"]}))
print(store.run_query("doing"))
```

## Live / async

### Optional asyncio wrappers

<a id="fn-asyncio"></a>

Wrappers use asyncio.to_thread. They do not change single-writer guarantees. Do not call them from inside a query/mutation body.

```python
import asyncio
from ux_fnbase.asyncio import run_query, run_mutation

async def main():
    result = await run_query(store, "board")
    await run_mutation(store, "add", {"title": "from thread"})
    return result

asyncio.run(main())
```
