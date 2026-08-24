# Glossary

| Term | Meaning in this repository |
| --- | --- |
| **ux-fnbase** / `ux_fnbase` | Product name / import package under `src/ux_fnbase`. |
| **Function database** | A store whose primary API is pure query and mutation *functions*, not ad-hoc SQL or client-side cache keys. |
| **Query** | Registered read function. Must not write. Runs against a frozen snapshot. |
| **Mutation** | Registered write function. Single-writer; may insert/patch/delete. |
| **Read-set** | Set of tokens recorded while a query executes. |
| **Write-set** | Set of tokens produced by a mutation’s writes. |
| **Token** | `DocToken`, `IndexToken`, or `ScanToken` — unit of dependency tracking. |
| **Intersection** | `intersects(read_set, write_set)` — true ⇒ subscription must re-run. |
| **Generation** | Integer commit clock on the store. Advances only on successful commit. |
| **Phase** | `idle`, `query`, `mutation`, or `notify` — contextvar-enforced. |
| **Snapshot** | Immutable clone of tables at a generation; queries run against it. |
| **Working copy** | Per-mutation cloned tables; discarded if the mutation throws. |
| **Subscribe** | Register a callback for a named query + args; immediate fire + invalidation. |
| **Canonical form** | `canonical(value)` — sorted-key JSON used for equality and index keys. |
| **QueryState** | Wire-layer last legal query result (not MorphState). |
| **MutationDoor** | Wire-layer only path from product code into `Store.run_mutation`. |
| **LivePush** | Wire-layer Channel-*shaped* morph fanout; does not import `ux_channel`. |
| **seq** | Monotonic LivePush counter; survives generation reset; SSE `Last-Event-ID`. |
| **Intent** | Named product action `component.method` + args; allowlisted fail-closed. |
| **Isolation Law** | Import graph rules: core never imports UI; routes never import `ux_fnbase` directly. |
| **Fail closed** | On violation or uncertainty, raise or reject — never silent success. |
| **Residual** | Leftover wrong state after an error or race (e.g. partial commit, stalled waiter). |
| **Playground** | Reference host under `playground/`; not part of the installable core API. |
