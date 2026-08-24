# ux-fnbase

[![CI](https://github.com/bitplorer/ux-fnbase/actions/workflows/ci.yml/badge.svg)](https://github.com/bitplorer/ux-fnbase/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

Function database: pure-function queries and mutations, read-set tracking, ACID writes, live subscriptions.

Queries are ordinary Python functions. The runtime records every document, index key, and table scan they observe. Mutations are single-writer serializable. After a commit, only subscriptions whose **read-set intersects** the write-set re-run.

Inspired by the reactive-function model popularized by [Convex](https://www.convex.dev) (read-set invalidation, pure query/mutation functions). ux-fnbase is an independent pure-Python implementation with explicit fail-closed concurrency, not a Convex client or protocol clone.

| | |
| --- | --- |
| **Package** | `ux_fnbase` |
| **Version** | `0.1.0` |
| **Python** | ≥ 3.11 (tested 3.11–3.14) |
| **License** | [Apache-2.0](LICENSE) |
| **Deps (core)** | stdlib only |

**What it is for:** application backends and local-first UIs that want *backend as pure functions* — board views, live dashboards, multi-pane editors that stay consistent without a separate cache layer.

**What it is not:** a multi-node distributed database, a SQL engine, a Convex-compatible cloud service, or a UI framework. Multi-process and multi-host replication are out of scope for 0.1.0 (single process, single writer).

## Table of Contents

- [Install](#install)
- [Usage](#usage)
- [Why ux-fnbase](#why-ux-fnbase)
- [Family Python policy](#family-python-policy)
- [Repository layout](#repository-layout)
- [Documentation](#documentation)
- [Core concepts](#core-concepts)
- [Guarantees](#guarantees)
- [Hard limits](#hard-limits)
- [API](#api)
- [Playground / wire](#playground--wire)
- [Testing](#testing)
- [Versioning](#versioning)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## Install

Core has **no** third-party dependencies.

```bash
pip install -e .                 # from this repository
pip install -e ".[dev]"          # pytest, hypothesis, fastapi, httpx
pip install -e ".[playground]"   # FastAPI host helpers only
```

There is no published PyPI release required to use the tree:

```bash
cd ux-fnbase
export PYTHONPATH=src:.
python -c "from ux_fnbase import Store; print(Store)"
```

## Usage

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

@store.mutation
def add(ctx, title: str):
    return ctx.db.table("tasks").insert({
        "title": title,
        "status": "backlog",
    })

store.run_mutation("add", {"title": "Ship ux-fnbase"})
print(store.run_query("board"))

def on_change(result, meta):
    print("generation", meta.generation, "docs", len(result))

unsub = store.subscribe("board", None, on_change)
store.run_mutation("add", {"title": "Live update"})
unsub()
store.close()
```

Five-minute path: [docs/START_HERE.md](docs/START_HERE.md).

## Why ux-fnbase

| Problem | ux-fnbase answer |
| --- | --- |
| ORM + hand-rolled cache invalidation | Queries declare nothing; the runtime records reads |
| WebSocket fanout of “everything changed” | Precise token intersection — only affected subs re-run |
| Nested writes from reactive callbacks | Phase machine: notify-phase mutation → `NestedTransactionError` |
| Partial commit on disk failure | Persist-before-publish; pre-image rollback on durability failure |
| UI layer coupled to the database | Isolation Law: `ux_fnbase` never imports compose / MorphState / Channel |

## Family Python policy

| Package | `requires-python` | Notes |
| --- | --- | --- |
| **ux-compose** | `>=3.11` | Classifiers 3.11–3.14 |
| **ux-dom** | prefers **≥3.14** | Full DOM/runtime stack; L1 offline can run 3.11+ |
| **ux-channel / ux-behavior / ux-motion** | follow compose stack | Install with the product Python |
| **ux-fnbase** | **`>=3.11`** | Same floor as ux-compose; tested 3.11–3.14 |

ux-fnbase is a sibling data plane: it must run on every Python the compose host supports, without requiring ux-dom’s 3.14 floor when used alone.

## Repository layout

```
ux-fnbase/
├── src/ux_fnbase/        # Core library (stdlib only) — THE product
│   ├── store.py          # Store, phases, subscribe, durability
│   ├── tokens.py         # DocToken / IndexToken / ScanToken / intersects
│   ├── schema.py         # TableSchema, string, literal, integer
│   ├── ids.py            # 26-char ids
│   ├── canonical.py      # Deterministic JSON for equality / index keys
│   ├── errors.py         # Fail-closed exception hierarchy
│   └── __init__.py       # Public exports
├── playground/           # Optional demo composition root — NOT a ux-fnbase dep
├── tests/
├── docs/
└── pyproject.toml
```

**Rule:** product application code that only needs the database depends on `ux_fnbase`. The `playground/` package is a reference composition pattern for hypermedia UIs; it must never be imported by `src/ux_fnbase`.

## Documentation

Family contract: [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) (Diátaxis + Standard Readme + GitHub community files).

| You are… | Start |
|----------|--------|
| **New** | [docs/START_HERE.md](docs/START_HERE.md) |
| **Need the map** | [docs/INDEX.md](docs/INDEX.md) |
| **Need facts** | [docs/API.md](docs/API.md) · [docs/GUARANTEES.md](docs/GUARANTEES.md) |
| **Why it works this way** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| **Contributor / agent** | [CONTRIBUTING.md](CONTRIBUTING.md) · [AGENTS.md](AGENTS.md) |
| **Security reviewer** | [SECURITY.md](SECURITY.md) |
| **Questions** | [docs/FAQ.md](docs/FAQ.md) · [SUPPORT.md](SUPPORT.md) |

| Diátaxis | Pages |
|----------|--------|
| Tutorial | [docs/START_HERE.md](docs/START_HERE.md) |
| How-to | [docs/FAQ.md](docs/FAQ.md) · [docs/WIRE.md](docs/WIRE.md) · [docs/COMPOSE.md](docs/COMPOSE.md) |
| Reference | [docs/API.md](docs/API.md) · [docs/GUARANTEES.md](docs/GUARANTEES.md) · [docs/GLOSSARY.md](docs/GLOSSARY.md) |
| Explanation | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |

## Core concepts

1. **Tables** — named document collections with optional equality indexes and schema.
2. **Queries** — pure functions `@store.query def name(ctx, **args)`. They only read via `ctx.db`.
3. **Mutations** — `@store.mutation def name(ctx, **args)`. They only write via `ctx.db.table(...).insert|patch|delete`.
4. **Read-set** — tokens recorded while a query runs (`DocToken`, `IndexToken`, `ScanToken`).
5. **Write-set** — tokens emitted by a mutation’s inserts/patches/deletes.
6. **Subscribe** — re-runs a named query when read-set ∩ write-set is non-empty; skips equal canonical results.
7. **Generation** — monotonic commit counter; does not advance on thrown mutations.
8. **Phase** — `idle | query | mutation | notify`. Illegal crossings raise.

System fields on every document: `_id` (26-char), `_creationTime` (ms), `_generation` (commit that wrote the row). Application fields must not use names starting with `_`.

## Guarantees

| Guarantee | Status in 0.1.0 |
| --- | --- |
| Serializable mutations (single process) | Yes — exclusive write lock |
| Snapshot isolation for queries | Yes — snapshot under lock, then lock-free |
| No dirty reads | Yes |
| No lost updates between writers | Yes — single writer |
| Thrown mutation leaves store unchanged | Yes — working copy discarded |
| Notify-phase mutation rejected | Yes — `NestedTransactionError` |
| Durable file backend atomic replace | Yes — `AtomicJsonBackend` + pre-image rollback |
| Multi-process / multi-host consensus | **No** — not offered |
| Cryptographic auth / Caps | **No** — compose/wire concern, not ux-fnbase |

Full detail: [docs/GUARANTEES.md](docs/GUARANTEES.md).

## Hard limits

| Limit | Value |
| --- | --- |
| `MAX_DOC_BYTES` | 256_000 |
| `MAX_DOCS_PER_TABLE` | 100_000 |
| `MAX_TX_WRITES` | 10_000 |
| `MAX_QUERY_RESULTS` | 10_000 |
| `MAX_SUBSCRIPTIONS` | 10_000 |
| `MAX_JOURNAL` | 256 |
| `WRITE_LOCK_TIMEOUT_S` | 30.0 |

Exceeding a limit raises `LimitExceededError`. Limits are constants in `ux_fnbase.store` — change them only deliberately and with tests.

## API

Public names are exactly `ux_fnbase.__all__`:

| Export | Role |
|--------|------|
| `Store` | Tables, `@query` / `@mutation`, `run_query` / `run_mutation`, `subscribe` |
| `AtomicJsonBackend` | Durable file backend |
| `QueryMeta` | Subscription metadata (`generation`, …) |
| `TableSchema`, `string`, `literal`, `integer` | Optional schema |
| `new_id` | 26-character document ids |
| `DocToken`, `IndexToken`, `ScanToken`, `intersects` | Read/write-set tokens |
| `UxFnbaseError` and subclasses | Fail-closed errors |

Signatures: [docs/API.md](docs/API.md). Anything under `playground/` is reference code, not the public API.

## Playground / wire

`playground/` shows how to attach ux-fnbase to a hypermedia UI **without** importing Channel or MorphState into the database:

- `MutationDoor` — sole write path from product code
- `QueryBinding` — subscribe → `QueryState`
- `LivePush` — Channel-shaped morph fanout (`seq` monotonic across reset)
- `Intent` — fail-closed action allowlist (404 unknown, 400 illegal)

Isolation Law and residual table: [docs/COMPOSE.md](docs/COMPOSE.md), [docs/WIRE.md](docs/WIRE.md).

## Testing

```bash
export PYTHONPATH=src:.
python -m pytest -q
PYTHONPATH=src:. python benchmarks/bench_fanout.py --subscribers 25 --mutations 50
```

- `tests/` — store, tokens, ids, hypothesis properties, chaos, asyncio wrappers
- `playground/tests/test_isolation.py` — import graph Isolation Law
- `playground/tests/test_residuals.py` — race / reset / equal-gen / intent / view snapshot
- `.github/workflows/ci.yml` — pytest + benchmark smoke on 3.11–3.14

## Versioning

SemVer. `0.y.z` may include breaking API changes. Public API is the export list in `ux_fnbase.__all__`. See [CHANGELOG.md](CHANGELOG.md).

## Security

Core **trusts the caller**. It does not authenticate, authorize, encrypt, or mint Caps. See [SECURITY.md](SECURITY.md).

## Contributing

PRs are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) (setup, residual checklist) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Questions: [SUPPORT.md](SUPPORT.md). How the project is run: [GOVERNANCE.md](GOVERNANCE.md).

## License

Apache License 2.0 — see [LICENSE](LICENSE). Copyright the ux-fnbase contributors.
