# Wire adaptor (playground)

The wire lives under `playground/wire/`. It is **not** imported by `ux-fnbase` core. It shows how a UI host should talk to the store without violating Isolation Law.

## Modules

| Module | Types | Responsibility |
| --- | --- | --- |
| `bind.py` | `QueryState`, `MutationDoor`, `QueryBinding`, `GenerationFanout`, `bind_query` | Subscribe + exclusive write door + optional gen clock |
| `live.py` | `LivePush`, `MorphOp` | Channel-shaped morph fanout; monotonic `seq` |
| `intent.py` | `IntentError`, `collect_actions`, `require_action` | Fail-closed HTTP/action names |

## QueryState

Last legal result of a subscribed query:

- `result`, `generation`, `name`, `elapsed_ms`, `read_set`, `error`  
- `snapshot()` → deep copy for render consistency  

**Not** MorphState. Domain documents must not be stored in UI dirty-bit state.

## MutationDoor

```python
door = MutationDoor(store)
door.run("add_task", {"title": "x", "author": "north"})
door.query("board")  # one-shot; not a subscription
```

- Empty / non-string mutation name → `SchemaViolationError`  
- Non-dict args (when not `None`) → `SchemaViolationError`  
- Nested use from notify still hits store phase checks  

Product code should not call `store.run_mutation` if a door is provided.

## QueryBinding

```python
binding = bind_query(store, "board", on_change=fn, fanout=live)
binding.detach()  # idempotent
```

- Attaches `store.subscribe`  
- Copies result into `binding.state`  
- Publishes generation to `fanout` if provided (equal gen → no-op on LivePush)  
- `on_change` must not call `MutationDoor.run`

## LivePush

Channel **analogue** — does not import `ux_channel`.

| Method | Role |
| --- | --- |
| `publish(generation)` | ux-fnbase clock from QueryBinding; **no-op if generation ≤ current** |
| `publish_morph(target, generation, html)` | After HTTP render; rejects stale generation |
| `wait_after(seen_seq)` | SSE wait on monotonic **seq** |
| `wait_morph_at_least(generation, timeout=…)` | Bridge notify clock → HTML publish race |
| `begin_reset()` | Clear morphs + generation clock; **does not notify** (store not ready) |
| `reopen()` / `close()` | Test / shutdown helpers |

Morph wire shape:

```json
{
  "op": "morph",
  "target": "#stage",
  "html": "<div id=\"stage\">...</div>",
  "generation": 12,
  "seq": 40
}
```

If HTML exceeds `MAX_MORPH_CHARS` (1_000_000), `op` becomes `"tick"` and `html` is empty — client should fetch a fragment.

**Why `seq` exists:** store `generation` may return to low values after `HOST.reset()`. SSE `Last-Event-ID` must not stall. `seq` never decreases on `begin_reset`.

## Intent

```python
allowed = collect_actions({"stage": component_instance})
require_action("stage.add", allowed)  # or IntentError
```

- Legal name pattern: `^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$`  
- Unknown → status **404**  
- Illegal → status **400**  
- Only methods marked `_ux_action = True` (as set by `@action` shims) are collected  

Silent no-ops for unknown actions are forbidden.

## Host (`playground.host.HOST`)

- Owns `LivePush`, `Store` (via `create_demo_store`), bindings, `QueryState` board/stats.  
- `view()` — one locked snapshot of board+stats for a single render (closes split-generation residual).  
- `reset()` — detach → close store → `live.begin_reset()` → new store → bind → `live.publish(generation)`.  
- `mutate` / `chaos` / `journal` / `explain_board` / `runtime`.

## Residuals closed (wire)

| Residual | Guard | Test |
| --- | --- | --- |
| Notify before HTML | `wait_morph_at_least` | `test_wait_morph_closes_notify_render_race` |
| Reset stalls waiters | monotonic `seq` + `begin_reset` quiet | `test_seq_survives_begin_reset` |
| Double seq on board+stats | equal-gen publish no-op | `test_two_bindings_one_seq_bump` |
| Split lab generation | `HOST.view()` | `test_host_view_consistent_snapshot` |
| Unknown actions | Intent | `test_intent_fail_closed` |

## What the wire does not do

- Does not mint Caps or verify signatures  
- Does not run idiomorph (browser / host JS does)  
- Does not start mutations from SSE  
- Does not import `ux_compose` or `ux_channel`  
