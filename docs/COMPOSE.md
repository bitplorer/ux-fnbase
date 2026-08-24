# ux-fnbase × ux-compose

**ux-fnbase** is a reactive function database. [ux-compose](https://github.com/bitplorer/ux-compose) is a composition root (MorphState, `@action`, Caps, Channel). They are **not** the same system.

## Place in the ux-* hierarchy

| Layer | Role |
| --- | --- |
| `ux-dom` | Document SSoT, elements |
| `ux-channel` | Live Caps, Intent transport, ASGI |
| `ux-behavior` | MorphState, `@action`, Cap Law |
| `ux-motion` | Presence / transition plans |
| `ux-compose` | App composition root (harnesses specialists) |
| **`ux-fnbase`** | **Function database** — sibling data plane, not a compose specialist |

ux-fnbase is **not** imported by ux-compose core, and does not import any ux-* UI package.

## Isolation Law

| Package | May import | Must not import |
| --- | --- | --- |
| `ux_fnbase` | stdlib only | `ux_compose`, `playground`, MorphState, Channel |
| `playground.wire` | `ux_fnbase` | `ux_compose`, MorphState, Caps, Channel |
| `playground.host` | `ux_fnbase`, `playground.wire` | Channel |
| product routes / components | host doors (`HOST`) | `ux_fnbase` directly |

```
[ Component / @action ]
         │
         ▼
  playground.host
         │
  ┌──────┼──────────┐
  ▼      ▼          ▼
 QueryBinding  MutationDoor  LivePush
  │            │             │
  subscribe    run_mutation  MorphOp (SSE)
         │
         ▼
   ux_fnbase.Store
```

## Three joins

| Direction | Meaning |
| --- | --- |
| Subscriptions → `QueryState` | Read path |
| `@action` → `MutationDoor` | Write path |
| LivePush / SSE → morph ops | Delivery path (Channel-shaped; no `ux_channel` import) |

`QueryState` is **not** MorphState. Domain documents stay in ux-fnbase.

See [WIRE.md](WIRE.md) for residual guards and tests.
