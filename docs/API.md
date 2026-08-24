# Public API reference

Version: **0.1.0**  
Package: **`ux_fnbase`**  
Source of export list: `src/ux_fnbase/__init__.py` (`__all__`).

Anything not listed in `__all__` is internal and may change without notice.

---

## Install / import

```python
from ux_fnbase import (
    Store,
    AtomicJsonBackend,
    TableSchema,
    string,
    literal,
    integer,
    QueryMeta,
    DocToken,
    IndexToken,
    ScanToken,
    intersects,
    new_id,
    # errors — see below
)
```

Core depends on the Python standard library only.

---

## `Store`

```python
Store(backend: AtomicJsonBackend | None = None)
```

In-memory function database. Optional `backend` loads at construction and saves after every successful commit.

### Schema registration

```python
store.define_table(
    name: str,
    *,
    indexes: tuple[str, ...] | list[str] = (),
    schema: TableSchema | None = None,
) -> None
```

- Creates a table.  
- **Idempotent** if the same `indexes` and `schema` are registered again.  
- Raises `TableExistsError` if the name exists with **different** indexes/schema.  
- Indexes are **equality** indexes on a single field name (string key into the document).

### Registering functions

```python
@store.query
def board(ctx): ...

@store.query(name="board_v2")
def board_impl(ctx): ...

@store.mutation
def add_task(ctx, title: str): ...
```

- Default name is `fn.__name__`.  
- Raises `FunctionExistsError` on duplicate names.  
- Query signature: `(ctx, **args)` or `(ctx)` when args are `None`.  
- Mutation signature: same pattern; `ctx.db` is a `MutationSession`.

### Running

```python
store.run_query(name: str, args: Any = None) -> Any
store.run_mutation(name: str, args: Any = None) -> Any
store.explain(name: str, args: Any = None) -> dict
```

`args`:

- `None` — call `fn(ctx)`  
- `dict` — call `fn(ctx, **args)`  
- other — call `fn(ctx, args)`  

`explain` returns:

```python
{
  "result": Any,
  "generation": int,
  "elapsed_ms": float,
  "read_set": list[dict],  # token dicts
  "name": str,
}
```

### Subscribe

```python
unsub = store.subscribe(
    name: str,
    args: Any,
    callback: Callable[[Any, QueryMeta], None],
) -> Callable[[], None]
```

- Validates query name (`FunctionNotFoundError`).  
- Fires **immediately** with the current snapshot (phase `query`, not `notify`).  
- On each successful mutation, re-runs if read-set intersects write-set and canonical result changed.  
- If `callback` raises during notify, **that subscription is removed**; the store continues.  
- If `callback` raises during the immediate fire, the subscription is not kept.  
- Returns an idempotent-style unsubscribe callable (safe to call once; second call is a no-op on a missing id).

`QueryMeta` fields: `name`, `generation`, `elapsed_ms`, `read_set` (tuple of token dicts).

### Inspection

```python
store.generation -> int
store.stats() -> dict          # generation, subscriptions, queries, mutations, tables
store.journal() -> list[JournalEntry]
store.snapshot_documents(table: str) -> list[dict]
store.close() -> None          # marks closed; clears subscriptions
```

`JournalEntry`: `generation`, `name`, `ok`, `elapsed_ms`, `error`.

### Query context (`ctx` in queries)

```python
ctx.db.table(name) -> QueryTable
QueryTable.get(id) -> dict | None          # records DocToken
QueryTable.scan() -> QueryCursor           # records ScanToken
QueryTable.index(field).eq(value) -> QueryCursor  # records IndexToken
QueryCursor.collect() -> list[dict]        # deep copies; enforces MAX_QUERY_RESULTS
```

### Mutation context (`ctx` in mutations)

```python
ctx.db.table(name) -> MutationTable
MutationTable.insert(doc: dict) -> dict    # adds _id, _creationTime, _generation
MutationTable.patch(id: str, patch: dict) -> dict
MutationTable.delete(id: str) -> None
```

- `insert` / `patch` run schema validation when a `TableSchema` is defined.  
- Reserved application fields: do not put `_id`, `_creationTime`, `_generation` in schema field maps; system sets them.  
- Missing document on patch/delete → `DocumentNotFoundError`.

---

## `TableSchema` and validators

```python
TableSchema(fields: dict[str, Validator])
schema.validate(doc: dict, *, partial: bool = False) -> dict
```

- `partial=True` validates only provided non-`_` keys (used conceptually for patches after merge).  
- Unknown non-reserved keys → `SchemaViolationError`.  
- Missing required keys (full validate) → `SchemaViolationError`.

Built-ins:

```python
string(*, min_len: int = 0, max_len: int = 10_000) -> Validator
literal(*allowed: Any) -> Validator
integer(*, min_v: int | None = None, max_v: int | None = None) -> Validator
```

`integer` rejects `bool` (because `bool` is a subclass of `int` in Python).

---

## Tokens

```python
DocToken(table: str, id: str)
IndexToken(table: str, field: str, value: Any)
ScanToken(table: str)

intersects(reads, writes) -> bool
token.to_dict() -> dict  # {"kind": "doc"|"index"|"scan", ...}
```

Intersection rules (implementation in `ux_fnbase.tokens.intersects`):

| Read | Write | Intersects when |
| --- | --- | --- |
| `DocToken` | `DocToken` | same table and id |
| `IndexToken` | `IndexToken` | same table, field, and canonical value |
| `ScanToken` | any token on that table | always |
| any token on table | `ScanToken` on that table | always |

Mutations emit `DocToken`, index tokens for affected fields (old and new on patch), and a `ScanToken` for the table.

---

## `AtomicJsonBackend`

```python
AtomicJsonBackend(path: str)
backend.save(payload: dict) -> None
backend.load() -> dict | None
```

- Writes temp file in the same directory, `fsync`, then `os.replace` (atomic on the same filesystem).  
- Failure raises `DurabilityError`.  
- On save failure after in-memory apply, `Store` restores pre-images and does not keep the new generation.

Payload shape:

```json
{
  "generation": 3,
  "tables": {
    "tasks": {
      "indexes": ["status"],
      "docs": [ { "_id": "...", "...": "..." } ]
    }
  }
}
```

Schema objects are not serialized; after load, call `define_table` again with the same indexes (idempotent) if you need schema enforcement.

---

## `new_id`

```python
new_id(now_ms: int | None = None) -> str
```

26-character id: 10-char base32 time prefix (ms) + 16-char base32 entropy. Alphabet excludes ambiguous characters (`ILOU`).

---

## Errors

All inherit `UxFnbaseError` unless noted.

| Type | When |
| --- | --- |
| `UxFnbaseError` | Base |
| `PhaseError` | Operation not allowed in current phase; write lock timeout |
| `NestedTransactionError` | `run_mutation` while phase ≠ `idle` |
| `SchemaViolationError` | Schema / validator / bad mutation door args |
| `FunctionNotFoundError` | Unknown query or mutation name |
| `FunctionExistsError` | Duplicate registration |
| `TableNotFoundError` | Unknown table |
| `TableExistsError` | Conflicting `define_table` |
| `DocumentNotFoundError` | patch/delete missing id |
| `StoreClosedError` | Use after `close()` |
| `DurabilityError` | Backend save failed (state rolled back) |
| `LimitExceededError` | Hard limit hit |

---

## Phases (caller rules)

| You are… | Allowed |
| --- | --- |
| Outside store (`idle`) | `run_query`, `run_mutation`, `subscribe` |
| Inside query function | table reads only |
| Inside mutation function | table writes only (no `run_query` / nested `run_mutation`) |
| Inside subscriber callback after a commit | reads via query path OK; **`run_mutation` forbidden** |

---

## Threading model

- One exclusive write lock for mutations (`WRITE_LOCK_TIMEOUT_S`).  
- Query snapshot is taken under a store lock, then the query body runs without holding the write lock.  
- Safe for multi-threaded readers + single writer in one process.  
- Not a multi-process database: multiple OS processes need external coordination (not provided).

---

## Optional asyncio helpers (`ux_fnbase.asyncio`)

Not in `__all__` — import explicitly. Wrappers call the **same** sync Store via `asyncio.to_thread`. Guarantees unchanged.

```python
from ux_fnbase.asyncio import run_query, run_mutation, explain, subscribe_once

result = await run_query(store, "board")
await run_mutation(store, "add", {"title": "x"})
info = await explain(store, "board")
rows, meta = await subscribe_once(store, "board", timeout=5.0)
```

Do not call these from inside a query or mutation body. Long-lived subscriptions should still use `Store.subscribe` with a queue or dedicated thread.
