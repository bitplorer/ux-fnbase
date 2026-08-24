# Guarantees and non-guarantees

This document is the contract operators and tests may rely on for **ux-fnbase 0.1.0**.

## Isolation and concurrency

| Claim | Guaranteed? | Mechanism |
| --- | --- | --- |
| Serializable mutations in one process | **Yes** | Single exclusive writer |
| Snapshot isolation for a single query function | **Yes** | Snapshot under lock; body lock-free |
| No dirty reads | **Yes** | Queries never see working copies |
| No lost updates between concurrent writers | **Yes** | Writers cannot interleave |
| No write skew across multiple objects in one mutation | **Yes** | One mutation sees its own working copy only; commits atomically |
| Repeatable read across *two sequential* `run_query` calls | **No** | Each call takes a new snapshot; generation may advance between them |
| Multi-process linearizability | **No** | Not implemented |
| Distributed consensus / HA | **No** | Out of scope |

## Failure behavior

| Situation | Behavior |
| --- | --- |
| Mutation raises before commit | Working copy discarded; generation unchanged; journal `ok=False` |
| Backend `save` fails after memory apply | Pre-images restored; generation restored; `DurabilityError` |
| Subscriber callback raises in notify | That subscription removed; store remains up; other subs continue |
| Subscriber callback raises on immediate subscribe | Subscription not retained; error propagates |
| Nested `run_mutation` | `NestedTransactionError` |
| Unknown function name | `FunctionNotFoundError` |
| Limit exceeded | `LimitExceededError` |
| Use after `close()` | `StoreClosedError` |

## Reactivity

| Claim | Guaranteed? |
| --- | --- |
| Subscription re-runs when its read-set intersects the commit write-set | **Yes** |
| Subscription does not re-run when there is no intersection | **Yes** (after first delivery) |
| Subscription does not invoke callback when canonical result is unchanged | **Yes** |
| Scan-based queries may re-run on any write to that table | **Yes** (conservative by design) |
| Fairness / latency SLOs under load | **No** numeric SLO in 0.1.0 |

## Durability

| Claim | Guaranteed? |
| --- | --- |
| With no backend | Process memory only; restart loses data |
| With `AtomicJsonBackend` on local POSIX FS | Last successful commit is on disk after `save` returns |
| Crash mid-`rename` | OS-level: either old or new file; not a torn JSON body for replace |
| Crash mid-write before `replace` | Temp file may remain; target unchanged |
| Schema round-trip in JSON file | **No** — schema must be re-`define_table`d after load |

## Limits

Configured in `ux_fnbase.store`:

| Constant | Default | On exceed |
| --- | --- | --- |
| `MAX_DOC_BYTES` | 256_000 | `LimitExceededError` |
| `MAX_DOCS_PER_TABLE` | 100_000 | `LimitExceededError` |
| `MAX_TX_WRITES` | 10_000 | `LimitExceededError` |
| `MAX_QUERY_RESULTS` | 10_000 | `LimitExceededError` |
| `MAX_SUBSCRIPTIONS` | 10_000 | `LimitExceededError` |
| `MAX_JOURNAL` | 256 | oldest journal entries dropped |
| `WRITE_LOCK_TIMEOUT_S` | 30.0 | `PhaseError` |

## Security (core)

ux-fnbase core does **not** implement authentication, authorization, encryption, or capability tokens. Any process that can call `run_mutation` is fully trusted. See [SECURITY.md](../SECURITY.md).

## Compatibility

| Claim | Policy |
| --- | --- |
| Python | ≥ 3.11 (aligned with ux-compose; CI 3.11–3.14) |
| Public API | `ux_fnbase.__all__` only |
| Wire JSON of tokens | `kind` + fields as in `token.to_dict()`; may add fields later, will not remove `kind` without major version |
| Id format | Opaque 26-char strings; do not parse structure in application code |

## References

* Berenson et al., “A Critique of ANSI SQL Isolation Levels”, 1995  
* Adya, “Weak Consistency: A Generalized Theory and Optimistic Implementations for Distributed Transactions”, 1999  
