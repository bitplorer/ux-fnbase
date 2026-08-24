## What

<!-- One paragraph. Name the public API, CLI, or doc path you changed. -->

## Why

<!-- Invariant, bug, or reader task this unblocks. -->

## Layer check

- [ ] This change belongs in **this** repository (ownership table in README).
- [ ] I did not reimplement a sister layer (DOM / Channel / Behavior / Motion / Compose / Fnbase).

## Docs (Diátaxis)

- [ ] Tutorial / START_HERE still succeeds in five minutes if I touched onboarding.
- [ ] How-to still matches the commands I run.
- [ ] Reference matches `__all__` / CLI / wire (no invented names).
- [ ] Explanation updated only if I changed a *why*.
- [ ] README links still resolve to canonical pages (not `Moved` stubs).

## Tests

Commands I ran:

```bash
# paste
```

Expected result: 

## Security

- [ ] No secrets in the diff.
- [ ] Fail-closed paths still raise (no silent success).
