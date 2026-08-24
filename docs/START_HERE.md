# Start here (5 minutes)

**ux-fnbase** is a *function database*: you write pure Python query and mutation functions; the runtime tracks what each query read and only re-runs subscriptions when those reads are affected by a commit.

## Who this is for

| You are… | You want… |
| --- | --- |
| Backend / full-stack Python | Live views without hand-rolled cache keys |
| Local-first / single-process apps | Serializable writes + snapshot reads |
| ux-compose / hypermedia authors | A data plane that never imports MorphState or Channel |
| Agent / CI | A package with Isolation Law tests and a fixed public `__all__` |

## Who this is *not* for (yet)

- Multi-node distributed consensus  
- SQL / Postgres replacement  
- Convex Cloud protocol compatibility  
- Auth, Caps, or multi-tenant security (host responsibility)

## 60-second mental model

```
define_table → @query / @mutation → run_query / run_mutation → subscribe
                     │                        │
              records read-set          emits write-set
                     └──────── intersects? ───┘
                              │ yes → re-run sub
```

1. **Query** — pure function; may only read.  
2. **Mutation** — single writer; may insert/patch/delete.  
3. **Subscribe** — callback when read-set ∩ write-set is non-empty and the canonical result changed.  
4. **Fail closed** — nested mutation from a subscriber raises; thrown mutation does not advance generation.

**Cookbook:** [SNIPPETS.md](SNIPPETS.md) — Store, schema, tokens, durability, fail-closed errors, asyncio.

## Run the smallest example

```bash
cd ux-fnbase
export PYTHONPATH=src:.
python - <<'PY'
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

@store.mutation
def add(ctx, title: str):
    return ctx.db.table("tasks").insert({"title": title, "status": "backlog"})

store.run_mutation("add", {"title": "hello"})
print(store.run_query("board"))
store.close()
PY
```

## Next reads (in order)

1. [../README.md](../README.md) — badges, install, layout  
2. [GLOSSARY.md](GLOSSARY.md) — shared words  
3. [ARCHITECTURE.md](ARCHITECTURE.md) — phases and tokens  
4. [API.md](API.md) — exact signatures  
5. [GUARANTEES.md](GUARANTEES.md) — what you may rely on  
6. [COMPOSE.md](COMPOSE.md) — place in the ux-* family (only if you use compose)

## Prove the tree

```bash
export PYTHONPATH=src:.
python -m pytest -q
python benchmarks/bench_fanout.py --subscribers 10 --mutations 20
```

## Common footguns

| Footgun | What happens |
| --- | --- |
| Call `run_mutation` inside a subscriber | `NestedTransactionError` |
| Expect multi-process locking | Not provided — single process only |
| Put domain docs in MorphState | Isolation Law violation; use `QueryState` via wire |
| Parse `_id` structure | Opaque string — do not depend on encoding |
| Assume schema survives JSON backend load | Re-`define_table` after load |

## Support path

- Bugs / design: GitHub Issues on this repo  
- Security: [SECURITY.md](../SECURITY.md)  
- Contributing: [CONTRIBUTING.md](../CONTRIBUTING.md)  
