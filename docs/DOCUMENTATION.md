# Documentation standard

This file is the **family documentation contract** for the UX stack
(`ux-dom`, `ux-channel`, `ux-behavior`, `ux-motion`, `ux-fnbase`, `ux-compose`).
It is the improved prompt we actually run: research first, then write, then
verify against code.

Out of scope for this round: `ux-app`, `ux-motion-lib`.

---

## 1. Research bar (do this before writing)

| Source | What we take from it |
|--------|----------------------|
| [Diátaxis](https://diataxis.fr/) | Four types: tutorial, how-to, reference, explanation. Do not mix modes in one page. |
| [Standard Readme](https://github.com/RichardLitt/standard-readme/blob/main/spec.md) | README section **order**. License **last**. Install + Usage with real code blocks. |
| [GitHub community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file) | `README`, `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, `SUPPORT`, issue + PR templates, `LICENSE`. |
| [Keep a Changelog](https://keepachangelog.com/) + [SemVer](https://semver.org/) | `CHANGELOG.md`. `0.y.z` may break; freeze is `__all__`. |
| Gold READMEs | [FastAPI](https://github.com/fastapi/fastapi), [httpx](https://github.com/encode/httpx), [pydantic](https://github.com/pydantic/pydantic) — install, a running example in under a screen, links into a map, contributing, license. |

**Diátaxis axes**

|  | Acquisition (study) | Application (work) |
|--|---------------------|--------------------|
| **Practice** | Tutorial — hold the reader's hand | How-to — a competent user has a goal |
| **Theory** | Explanation — why | Reference — facts that mirror the code |

Crossing those boundaries is the usual way docs rot.

---

## 2. Audiences (every concern has a door)

Every library must be enterable in **two clicks from the repository root**.

| Audience | Door | Success |
|----------|------|---------|
| First-time user | `START_HERE.md` + README Usage | Something runs in ~5 minutes |
| Experienced user | `docs/` how-to + reference | A task gets done without rereading the tutorial |
| Contributor | `CONTRIBUTING.md` + `AGENTS.md` | Tests + which doc to update |
| Security reviewer | `SECURITY.md` | Threat model, reporting path, what this layer does *not* promise |
| Operator | doctor / verify / ship docs | How to know the install is healthy |
| Agent / tooling | `docs/INDEX.md` + public `__all__` | Frozen names, ownership, no stub citations |

If a reader type cannot find themselves on the README audience table, the README is unfinished.

---

## 3. Required files (GitHub-mature)

| File | Role |
|------|------|
| `README.md` | Standard Readme. Short description < 120 characters. ToC. Install. Usage. API. Contributing. **License last.** |
| `START_HERE.md` | Tutorial door (5 minutes). One promise. |
| `docs/INDEX.md` | Only map. Diátaxis + audience. Sister-layer table. |
| `CONTRIBUTING.md` | Setup, public API rule, residual tests, PR checklist. |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1. |
| `SECURITY.md` | Supported versions, threat model, private reporting. |
| `SUPPORT.md` | Where to ask; what not to file as issues. |
| `CHANGELOG.md` | Keep a Changelog. |
| `LICENSE` | SPDX in README last section. |
| `.github/ISSUE_TEMPLATE/` | Bug + feature forms; `config.yml` routes security and support. |
| `.github/PULL_REQUEST_TEMPLATE.md` | Layer check + docs checklist. |
| `GOVERNANCE.md` | Who decides, how API freezes work. |

Canonical pages live in the Diátaxis folder for their mode.
`Moved (Phase 2 Diátaxis)` stubs may exist so old links resolve — **never cite a stub**.

---

## 4. Accuracy law

1. Public names come from `{package}.__all__` (and the CLI entry in `pyproject.toml`). Inventing a helper that is not exported is a docs bug.
2. Versions, `requires-python`, extras, and license come from `pyproject.toml` / `LICENSE`.
3. Ownership tables must match `docs/FLOW.md` (compose) and each README. Do not flatten sister layers into this repo.
4. If code and docs disagree, **code wins** — then the same change fixes the doc.
5. Examples must be copy-pasteable. Prefers `pip install` first, repo-tree second.

---

## 5. README order (Standard Readme)

1. Title (`#` matching the GitHub repo / PyPI name)
2. Badges (no heading)
3. Short description (own line, < 120 chars, no blockquote-only description)
4. Long description (what it is / is not, ownership)
5. Table of Contents (required if the file is ≥ 100 lines)
6. Install (code block)
7. Usage (code block; CLI if any)
8. Extra sections (audience, stack, guarantees, docs map, testing)
9. API (exported names)
10. Contributing
11. License (**must be last**)

---

## 6. Push rules (this family)

- Push via the **GitHub connector** only.
- **One agent. One repository at a time.** No concurrent multi-agent push.
- Do not document `ux-app` or `ux-motion-lib` in this pass.
