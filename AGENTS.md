# Agent notes (ux-fnbase)

## Identity

| | |
| --- | --- |
| PyPI | `ux-fnbase` |
| Import | `ux_fnbase` |
| Role | Function database — sibling data plane to ux-compose |
| Python | `>=3.11` |

## Hard laws

1. **`src/ux_fnbase` is stdlib-only.** Never add UI, HTTP, MorphState, or Channel imports to core.  
2. **Public API = `ux_fnbase.__all__` only.**  
3. **Fail closed.** Nested mutations, wrong phases, limit hits, and durability failures raise or roll back.  
4. **Isolation Law** (see `docs/COMPOSE.md`): product routes use host doors; they do not import `ux_fnbase` directly when following the playground pattern.  
5. **Docs track code.** Behavior change ⇒ update `docs/API.md` and/or `docs/GUARANTEES.md` in the same change.

## Do not

- Invent multi-process or distributed guarantees  
- Swallow exceptions in notify in a way that leaves partial commits  
- Parse document `_id` structure in application logic  
- Put domain documents into MorphState  

## Verify before claiming done

```bash
export PYTHONPATH=src:.
python -m pytest -q
python -c "from ux_fnbase import Store; print(Store)"
```

Isolation: `playground/tests/test_isolation.py` must stay green.

## Map

- Onboarding humans: `docs/START_HERE.md`  
- Contracts: `docs/GUARANTEES.md`, `docs/API.md`  
- Compose boundary: `docs/COMPOSE.md`, `docs/WIRE.md`  
