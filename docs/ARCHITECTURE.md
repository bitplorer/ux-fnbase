# Architecture

ux-fnbase is a **fail-closed reactive function database** in pure Python.

Queries and mutations are ordinary functions. The runtime records every
document, index key, and table scan a query observes. After a commit, only
subscriptions whose read-set intersects the write-set re-run.

## Design goals

1. **Backend as pure functions** — application logic is `@query` / `@mutation`, not scattered SQL and cache keys.  
2. **Precise invalidation** — no global “refetch all”.  
3. **Fail closed** — illegal phases, nested writes, and durability failures raise or roll back; they never partially succeed silently.  
4. **Zero core dependencies** — stdlib only inside `src/ux_fnbase`.  
5. **UI-agnostic core** — no MorphState, Channel, or HTTP inside the store.

## Component diagram

```
┌─────────────────────────────────────────────┐
│                 Application                  │
│         run_query / run_mutation /           │
│              subscribe(callback)             │
└─────────────────────┴──────────────────────┘
                      │
┌─────────────────────┴──────────────────────┐
│                   Store                      │
│  define_table · register query/mutation      │
│  generation · journal · optional backend     │
│                                              │
│  Phase (contextvar): idle|query|mutation|notify
│  Write lock: exclusive for mutations         │
└───────────┴────────────────────┴────────────┘
            │                     │
   ┌────────┴────────┐   ┌────────┴────────┐
   │  Snapshot query │   │ MutationSession │
   │  QueryTable     │   │ working copies  │
   │  read tokens →  │   │ write tokens →  │
   └────────┴────────┘   └────────┴────────┘
            │                     │
            └──────────┴──────────┘
                       │ intersects?
               ┌───────┴────────┐
               │   Notify loop  │
               │ re-run subs    │
               └────────────────┘
```

## Phase machine

```
idle ──run_query──► query ──► idle
idle ──run_mutation──► mutation ──persist──► commit ──► notify ──► idle
```

| Transition | Rule |
| --- | --- |
| Nested `run_mutation` | Forbidden unless phase is `idle` → `NestedTransactionError` |
| Query during `mutation` | `PhaseError` |
| Write APIs outside `mutation` | `PhaseError` |
| Subscriber calls `run_mutation` | Phase is `notify` → `NestedTransactionError` |

Phases are stored in contextvars (`ux_fnbase_phase`, `ux_fnbase_reads`, `ux_fnbase_writes`) so they follow the call stack on the same thread.

## Query path

1. Under the store lock, **clone** all tables into a `Snapshot` at the current generation.  
2. Set phase `query`, allocate an empty read-token buffer.  
3. Run the user function against `QueryContext` (lock-free relative to writers).  
4. Each `get` / `scan` / `index.eq` appends tokens to the buffer.  
5. Reset phase; return result + `QueryMeta` (includes read-set as dicts).

Queries never see another mutation’s working copy (no dirty reads).

## Mutation path

1. Acquire exclusive write lock (timeout → `PhaseError`).  
2. Phase `mutation`. Build `MutationSession` with lazy per-table clones.  
3. User function writes through `MutationTable.insert|patch|delete`, which:  
   - validates schema,  
   - updates working docs and equality indexes,  
   - appends write tokens (doc, index old/new, scan).  
4. On **success**, under the store lock:  
   - save pre-images of touched tables,  
   - install working tables,  
   - bump generation,  
   - if backend present: `save`; on failure restore pre-images, restore generation, raise `DurabilityError`,  
   - release paths and enter notify with the write-set.  
5. On **exception** before commit: discard working copies; generation unchanged; journal records failure.

## Notify path

1. Phase `notify`.  
2. Copy the subscription list under the store lock.  
3. For each subscription:  
   - re-run the query (`_run_query_inner`),  
   - if last result exists and read-set does **not** intersect write-set → skip,  
   - if canonical JSON of result equals last delivery → skip (no residual churn),  
   - else update last canonical and invoke callback.  
4. Callback exception → remove **that** subscription only.  
5. Phase back to `idle`.

## Token model

See also [API.md](API.md) and [GLOSSARY.md](GLOSSARY.md).

- **DocToken** — point dependency on one document.  
- **IndexToken** — equality membership in an index (value compared via `canonical`).  
- **ScanToken** — full-table observation; **conservative**: any write on that table invalidates scanners.

Under-invalidation is treated as a correctness bug. Over-invalidation (extra re-runs) is allowed for scan tokens.

## Equality and indexes

- Index keys are `canonical(field_value)` strings.  
- Result dedup for subscriptions uses `canonical(result)`.  
- Canonical form: `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True)` with no default handler for exotic types (non-JSON types fail closed).

## Identifiers

`new_id()` → 26 characters (10 time + 16 entropy), base32 alphabet without ambiguous glyphs. Not a ULID-compatible wire format guarantee; treat as opaque strings.

## Durability

`AtomicJsonBackend`:

1. Write temp file beside the target path.  
2. `flush` + `fsync`.  
3. `os.replace` onto the target (atomic on same filesystem).  

If step 3’s broader save path fails after memory commit, Store restores pre-images. **Do not** point the backend at a networked filesystem that breaks `rename` atomicity unless you accept the platform’s semantics.

## Journal

In-memory ring of the last `MAX_JOURNAL` (256) mutation attempts (`ok` / error / timing). Not durable unless you export it yourself. Intended for diagnostics and playground inspectors.

## References

* ANSI SQL isolation phenomena — Berenson et al., 1995  
* Snapshot isolation — Adya, 1999; PostgreSQL MVCC  
* Fine-grained reactive invalidation — SolidJS; Convex query subscriptions ([docs.convex.dev](https://docs.convex.dev))  
* Atomic replace — POSIX `rename(2)` on the same filesystem  
