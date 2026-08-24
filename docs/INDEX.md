# Documentation index

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

## Ownership

| Doc | Source of truth for |
| --- | --- |
| `API.md` | Public names and signatures |
| `ARCHITECTURE.md` | Phase machine and token rules |
| `GUARANTEES.md` | What tests and operators may assume |
| `WIRE.md` / `COMPOSE.md` | Playground boundaries (not core) |

If code and docs disagree, **code wins** — then fix the doc in the same change.
