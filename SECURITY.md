# Security

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes (best-effort while pre-1.0) |

## Threat model (core)

**ux-fnbase core trusts the caller.** Any code that can invoke `Store.run_mutation` or replace the backend path can read and write all data in that store.

Core does **not** provide:

- Authentication or session management
- Authorization or row-level security
- Encryption at rest or in transit
- Capability tokens (Caps) or signed Intents
- Sandboxing of query/mutation function bodies

Those belong in the host (HTTP door, compose Caps, OS permissions, etc.).

## What core *does* harden

| Topic | Behavior |
| --- | --- |
| Illegal concurrency | Nested mutations and wrong-phase ops raise |
| Oversized payloads | `LimitExceededError` at documented caps |
| Partial durable write | Pre-image rollback + `DurabilityError` |
| Schema enforcement | Optional `TableSchema` rejects bad fields/types |
| Subscription faults | Raising callback cancels only that subscription |

## Playground / wire

- Intent allowlist rejects unknown / illegal action names (no silent no-ops).
- LivePush does not execute mutations.
- HTML in MorphOps is whatever the host rendered; XSS prevention is the host’s escaping responsibility.

## Reporting

Report suspected vulnerabilities privately to the repository maintainers (GitHub Security Advisory if the repo is published, or the contact listed on the owning org profile). Please include:

- ux-fnbase version / commit
- Minimal reproduction
- Impact (data integrity, availability, isolation bypass)

Do not open public issues for unreleased vulnerability details.

## Dependencies

Core: **stdlib only** — no third-party supply chain in the default install.
Optional extras (`dev`, `playground`) pull pytest / FastAPI / etc.; pin and audit those in deploying applications.
