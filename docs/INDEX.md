# ux-fnbase documentation index

**Version 0.1.0** · **Start:** [START_HERE.md](START_HERE.md) (5 minutes)

This file is the map. If code and docs disagree, **code wins** — then fix the doc
in the same change. Family contract: [DOCUMENTATION.md](DOCUMENTATION.md).

## Folder contract (Diátaxis)

This package is small enough that pages live flat under `docs/`. Mode is in the
page, not a nested folder:

| Mode | Pages |
|------|-------|
| Tutorial | [START_HERE.md](START_HERE.md) |
| How-to | [FAQ.md](FAQ.md) · [WIRE.md](WIRE.md) (playground attach) · [COMPOSE.md](COMPOSE.md) |
| Reference | [API.md](API.md) · [GUARANTEES.md](GUARANTEES.md) · [GLOSSARY.md](GLOSSARY.md) |
| Explanation | [ARCHITECTURE.md](ARCHITECTURE.md) |

Do not cite a page as canonical if it is a `Moved` stub.

### Brand lines

| Layer | Name |
|-------|------|
| **PyPI / pip** | `ux-fnbase` |
| **Import** | `ux_fnbase` |
| **CLI** | *none (library)* |
| **Version** | `0.1.0` |
| **Python** | ≥ 3.11 (tested 3.11–3.14) |
| **License** | Apache-2.0 |

This layer **owns the function store**. It does not own Caps, HTML, MorphState, or product CLI.

---

## Audience

| You are… | Start (≤ 2 clicks) |
|----------|---------------------|
| **New** | [START_HERE.md](START_HERE.md) |
| **Need facts** | [API.md](API.md) · [GUARANTEES.md](GUARANTEES.md) |
| **Integrating with compose / hypermedia** | [COMPOSE.md](COMPOSE.md) · [WIRE.md](WIRE.md) |
| **Contributor / agent** | [../AGENTS.md](../AGENTS.md) · [../CONTRIBUTING.md](../CONTRIBUTING.md) |
| **Security** | [../SECURITY.md](../SECURITY.md) |

---

## Humans (first hour)

| Order | Doc | Why |
| --- | --- | --- |
| 1 | [START_HERE.md](START_HERE.md) | 5-minute mental model + smallest example |
| 2 | [../README.md](../README.md) | Install, layout, family Python policy |
| 3 | [FAQ.md](FAQ.md) | Convex? async? compose? production? |
| 4 | [GLOSSARY.md](GLOSSARY.md) | Shared vocabulary |
| 5 | [ARCHITECTURE.md](ARCHITECTURE.md) | Phases, tokens, commit/notify |
| 6 | [API.md](API.md) | Exact public signatures |
| 7 | [GUARANTEES.md](GUARANTEES.md) | Promises and non-promises |
| 8 | [COMPOSE.md](COMPOSE.md) / [WIRE.md](WIRE.md) | Only if integrating with ux-compose |

## Agents / contributors

| Doc | Why |
| --- | --- |
| [../AGENTS.md](../AGENTS.md) | Hard laws and verify commands |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Residual checklist, PR expectations |
| [../SECURITY.md](../SECURITY.md) | Threat model |
| [../CHANGELOG.md](../CHANGELOG.md) | What changed |
| [../SUPPORT.md](../SUPPORT.md) | Where humans ask questions |

## Ownership

| Doc | Source of truth for |
| --- | --- |
| `API.md` | Public names and signatures (`ux_fnbase.__all__`) |
| `ARCHITECTURE.md` | Phase machine and token rules |
| `GUARANTEES.md` | What tests and operators may assume |
| `WIRE.md` / `COMPOSE.md` | Playground boundaries (not core) |

## Sister layers

| Package | Role |
|---------|------|
| [ux-dom](https://github.com/bitplorer/ux-dom) | Render / Document |
| [ux-channel](https://github.com/bitplorer/ux-channel) | Intent → Cap → Result |
| [ux-behavior](https://github.com/bitplorer/ux-behavior) | Product behavior → Ops |
| [ux-motion](https://github.com/bitplorer/ux-motion) | Presence / transition plans |
| [ux-compose](https://github.com/bitplorer/ux-compose) | Composition + product CLI |

Do not flatten these layers into this repo.

## Community health

| File | Audience |
|------|----------|
| [../README.md](../README.md) | Everyone — Standard Readme door |
| [START_HERE.md](START_HERE.md) | First-time user |
| [../SUPPORT.md](../SUPPORT.md) | Questions |
| [../SECURITY.md](../SECURITY.md) | Security reviewers / reporters |
| [../CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | Everyone in the issue tracker |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Contributors |
| [../GOVERNANCE.md](../GOVERNANCE.md) | How decisions are made |
| [DOCUMENTATION.md](DOCUMENTATION.md) | Docs authors (the family contract) |
