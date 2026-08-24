# Contributing

Read [docs/START_HERE.md](docs/START_HERE.md) and [AGENTS.md](AGENTS.md) first.

## Principles

1. **Fail closed** — prefer raise / reject over silent success.
2. **Core stays pure** — `src/ux_fnbase` stdlib only; no UI imports.
3. **Docs track code** — if you change behavior, update `docs/` in the same change.
4. **Residuals need tests** — races and reset paths are not “obviously fine”.

## Setup

```bash
cd ux-fnbase
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export PYTHONPATH=src:.
python -m pytest -q
```

## Project rules

| Area | Rule |
| --- | --- |
| Public API | Only names in `ux_fnbase.__all__` |
| New store behavior | Add unit tests under `tests/` |
| Wire / Isolation Law | Add or extend `playground/tests/` |
| Import edges | Must keep AST isolation tests green |
| Limits | Changing `MAX_*` requires justification in the PR and GUARANTEES.md |

## Residual checklist

Before merging concurrency or subscription changes, verify:

- [ ] Notify-phase mutation still raises `NestedTransactionError`
- [ ] Thrown mutation does not advance `generation`
- [ ] Equal-generation `LivePush.publish` does not bump `seq`
- [ ] `begin_reset` does not wake waiters before a new store exists
- [ ] `HOST.view()` still returns one consistent board/stats snapshot
- [ ] Unknown Intent still 404; illegal name still 400

## Code style

- Python 3.11+ type hints where practical
- No silent `except:` that swallows store errors in core paths
- Prefer explicit phase checks over “shouldn’t happen” comments

## Pull requests

Include:

1. What invariant or feature changed
2. Test plan (commands + expected result)
3. Doc touch list (`API.md` / `GUARANTEES.md` / etc.)

## License

Contributions are under Apache-2.0 (see [LICENSE](LICENSE)).
