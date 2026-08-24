# ux-fnbase — snippets

> **Diátaxis:** how-to · copy-paste patterns from the public API (`__all__` / CLI).
> Map: see this package `docs/INDEX.md`.

Function database. Queries record a read-set. Mutations emit a write-set. Subscriptions re-run only on intersection.

Every block is meant to run (or to be the exact fragment you drop into a running app). Names are public exports. If code and this page disagree, **code wins**.

**11 snippets** covering install, core usage, fail-closed errors, live/async, CLI, and the usage patterns that keep layers from leaking.

### Public names in this cookbook

`Store`, `TableSchema`, `string`, `literal`, `AtomicJsonBackend`, `run_query`, `run_mutation`, `integer`, `new_id`, `DocToken`, `IndexToken`, `ScanToken`, `intersects`, `PhaseError`

## Contents

- [Install (stdlib core)](#fn-install)
- [Store, schema, query, mutation, subscribe](#fn-store)
- [Explain a query (read-set + generation)](#fn-explain)
- [Durable file backend (atomic replace)](#fn-durable)
- [get() and equality indexes](#fn-get-index)
- [integer schema + new_id](#fn-schema-id)
- [Read/write tokens and intersects()](#fn-tokens)
- [Fail-closed errors](#fn-errors)
- [Table / document / closed errors](#fn-table-errors)
- [Optional asyncio wrappers](#fn-asyncio)
- [Pattern: queries read, mutations write](#fn-pattern-purity)


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

### integer schema + new_id

<a id="fn-schema-id"></a>

integer() rejects bool (True is not an int). Unknown fields and missing fields raise SchemaViolationError.

```python
from ux_fnbase import Store, TableSchema, integer, string, new_id

store = Store()
store.define_table(
    "items",
    schema=TableSchema({
        "sku": string(min_len=1, max_len=32),
        "qty": integer(min_v=0, max_v=10_000),
    }),
)

@store.mutation
def stock(ctx, sku: str, qty: int):
    return ctx.db.table("items").insert({"sku": sku, "qty": qty})

row = store.run_mutation("stock", {"sku": "tee", "qty": 3})
print(row["_id"], new_id())   # _id is assigned on insert; new_id() is public
store.close()
```

### Read/write tokens and intersects()

<a id="fn-tokens"></a>

Subscriptions re-run only when read-set ∩ write-set is non-empty. ScanToken is conservative: any write on that table matches.

```python
from ux_fnbase import DocToken, IndexToken, ScanToken, intersects

reads = (ScanToken("tasks"),)
writes = (DocToken("tasks", "abc"), IndexToken("tasks", "status", "done"))
print(intersects(reads, writes))  # True — a scan of tasks sees any write on tasks

reads2 = (DocToken("tasks", "xyz"),)
print(intersects(reads2, writes))  # False — different document id
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

### Table / document / closed errors

<a id="fn-table-errors"></a>

define_table is idempotent only when indexes and schema match. delete() on a missing id raises DocumentNotFoundError.

```python
from ux_fnbase import (
    Store, TableExistsError, TableNotFoundError,
    DocumentNotFoundError, StoreClosedError, FunctionExistsError,
)

store = Store()
store.define_table("tasks")
try:
    store.define_table("tasks")
except TableExistsError:
    print("table exists")

@store.query
def board(ctx):
    return ctx.db.table("tasks").scan().collect()

try:
    @store.query
    def board(ctx):  # noqa: F811
        return []
except FunctionExistsError:
    print("query name taken")

@store.mutation
def drop(ctx, doc_id: str):
    ctx.db.table("tasks").delete(doc_id)

try:
    store.run_mutation("drop", {"doc_id": "missing"})
except DocumentNotFoundError:
    print("no such doc")

store.close()
try:
    store.run_query("board")
except StoreClosedError:
    print("closed")
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


## Usage patterns

### Pattern: queries read, mutations write

<a id="fn-pattern-purity"></a>

Phase machine is the product: query phase cannot write; notify phase cannot mutate. That is how nested-callback races die.

```python
from ux_fnbase import Store, PhaseError

store = Store()
store.define_table("tasks")

@store.query
def board(ctx):
    # legal: get / scan / index().eq().collect()
    return ctx.db.table("tasks").scan().collect()
    # illegal: ctx.db.table("tasks").insert({...})  → PhaseError

@store.mutation
def add(ctx, title: str):
    # legal: insert / patch / delete
    return ctx.db.table("tasks").insert({"title": title})
    # illegal: calling another mutation or subscribe() here → NestedTransactionError / PhaseError

store.close()
```
