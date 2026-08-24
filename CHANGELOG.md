# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-08-24

### Added

- **ux-fnbase** core store: tables, schema validators, queries, mutations, subscribe.
- Read-set tokens: `DocToken`, `IndexToken`, `ScanToken`, `intersects`.
- Phase machine: `idle` / `query` / `mutation` / `notify` with fail-closed nesting.
- `AtomicJsonBackend` with temp file + `os.replace` and pre-image rollback.
- Hard limits (`MAX_DOC_BYTES`, `MAX_DOCS_PER_TABLE`, …) raising `LimitExceededError`.
- 26-character ids via `new_id`.
- Canonical JSON helper for index keys and subscription equality.
- Playground wire: `QueryBinding`, `MutationDoor`, `LivePush`, Intent allowlist.
- Playground host + demo task board schema.
- Isolation Law AST tests and residual-closure tests.
- Full documentation set under `docs/`.
- Hypothesis property suite (`tests/test_properties.py`).
- Chaos / concurrent-reader suite (`tests/test_chaos.py`).
- Optional asyncio wrappers (`ux_fnbase.asyncio`) without changing sync guarantees.
- Formal subscription fanout benchmark (`benchmarks/bench_fanout.py`).
- GitHub Actions CI (pytest + benchmark smoke).

### Notes

- Formerly prototyped under the working name “Helix”; public name is **ux-fnbase** (function database; ux-* family).
- Single-process only; not a distributed database.

## [Unreleased]

### Changed

- Python floor raised to **>=3.11** for parity with ux-compose (classifiers + CI: 3.11, 3.12, 3.13, 3.14).

### Planned (non-binding)

- Optional formal hypothesis profile in CI nightlies with higher `max_examples`
- Published p50/p95 numbers per release on a fixed reference machine
