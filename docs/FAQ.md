# FAQ

## Is this Convex for Python?

**Conceptually adjacent, not compatible.** Both use pure query/mutation functions and read-set style invalidation. ux-fnbase is an independent pure-Python store with an explicit phase machine and fail-closed nesting. It does not speak the Convex wire protocol or host Convex UDFs.

## Does it need a server?

No. Core is an in-process library. Optional `AtomicJsonBackend` persists one JSON snapshot file. HTTP/SSE belongs in the host (see playground wire), not in `ux_fnbase`.

## Can I use it with ux-compose?

Yes, as a **sibling**. Compose must not import the store into MorphState. Use `playground.host` / wire patterns: `MutationDoor`, `QueryBinding`, `LivePush`. See [COMPOSE.md](COMPOSE.md).

## Why not SQL?

The product surface is *functions*, not queries-as-strings. That is intentional: dependency tracking is automatic, and the API stays small. You can still model relational data as tables + indexes.

## Is it production-ready?

**0.1.0 / Alpha.** Single-process guarantees are tested (including chaos and properties). There is no multi-node story, no auth, and no published SLO. Suitable for prototypes, embedded apps, and carefully bounded services.

## Thread safety?

Multiple reader threads + one writer in one process are supported. Mutations take an exclusive lock. Do not share a Store across processes without external coordination.

## Async?

Use `ux_fnbase.asyncio` wrappers (`run_query`, `run_mutation`, …). They call the same sync Store via `asyncio.to_thread`. Guarantees are unchanged.

## Why Apache-2.0 while some ux-* packages are MIT?

ux-fnbase ships Apache-2.0. Mixing licenses in an application is normal; respect both. If you need a dual-license discussion, open an issue.

## How do I version application queries?

Register a new function name (e.g. `board_v2`). There is no automatic migration framework in 0.1.0.

## What if a subscriber raises?

That subscription is removed; the store continues. Other subscribers are unaffected.
