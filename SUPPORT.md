# Support

**ux-fnbase** is maintained at [github.com/bitplorer/ux-fnbase](https://github.com/bitplorer/ux-fnbase).

## Where to go

| You want | Go here |
|----------|---------|
| Five-minute success | [START_HERE.md](START_HERE.md) (or `docs/START_HERE.md`) |
| The map | [docs/INDEX.md](docs/INDEX.md) |
| Usage that looks like a bug | GitHub issue — use the **Bug report** form |
| A feature that stays in this layer | GitHub issue — **Feature request** form |
| A question / “how do I” | Read the how-to index first; then a Discussion or a usage issue with what you already tried |
| A vulnerability | [SECURITY.md](SECURITY.md) **only** — never a public issue |
| Conduct | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |

Core has **no** runtime dependencies. If your bug needs FastAPI, say whether you installed the `playground` extra.

Root has no `START_HERE.md` — the tutorial door is [docs/START_HERE.md](docs/START_HERE.md).

## What not to file here

- Product lifecycle (`uxcompose create-app` / `serve` / `deploy`) belongs in [ux-compose](https://github.com/bitplorer/ux-compose).
- Intent / Caps / wire codecs belong in [ux-channel](https://github.com/bitplorer/ux-channel).
- HTML trees / `Document` belong in [ux-dom](https://github.com/bitplorer/ux-dom).
- MorphState / `@action` belong in [ux-behavior](https://github.com/bitplorer/ux-behavior).
- Motion IR belongs in [ux-motion](https://github.com/bitplorer/ux-motion).
- The function store belongs in [ux-fnbase](https://github.com/bitplorer/ux-fnbase).

Wrong-layer reports will be redirected, not ignored.

## Response

This is a small maintainer surface. Best-effort replies. A complete reproduction (version, Python, snippet) is the difference between a fix and a stalled thread.
