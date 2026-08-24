"""Read/write tokens for precise invalidation.

A query records every observation as a token. A mutation records every
effect. Subscriptions re-run only when read-set intersects write-set.

References
----------
* Fine-grained reactive invalidation — SolidJS; Convex query subscriptions
* Snapshot isolation — Adya, 1999
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, FrozenSet, Iterable


@dataclass(frozen=True, slots=True)
class DocToken:
    table: str
    id: str

    @property
    def kind(self) -> str:
        return "doc"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "doc", "table": self.table, "id": self.id}


@dataclass(frozen=True, slots=True)
class IndexToken:
    table: str
    field: str
    value: Any

    @property
    def kind(self) -> str:
        return "index"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "index",
            "table": self.table,
            "field": self.field,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class ScanToken:
    table: str

    @property
    def kind(self) -> str:
        return "scan"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "scan", "table": self.table}


Token = DocToken | IndexToken | ScanToken


def intersects(reads: Iterable[Token], writes: Iterable[Token]) -> bool:
    """True if any read token is affected by any write token.

    Rules
    -----
    * DocToken ↔ DocToken: same table + id
    * IndexToken ↔ IndexToken: same table + field + value
    * ScanToken ↔ anything on that table (conservative: full-table observation)
    * DocToken write ↔ IndexToken read: not direct; writers emit index tokens
      for old and new values so equality indexes invalidate correctly.
    """
    rset: FrozenSet[Token] = frozenset(reads)
    wset: FrozenSet[Token] = frozenset(writes)
    if not rset or not wset:
        return False

    r_scans = {t.table for t in rset if isinstance(t, ScanToken)}
    w_scans = {t.table for t in wset if isinstance(t, ScanToken)}
    if r_scans & {t.table for t in wset}:
        return True
    if w_scans & {t.table for t in rset}:
        return True

    r_docs = {(t.table, t.id) for t in rset if isinstance(t, DocToken)}
    w_docs = {(t.table, t.id) for t in wset if isinstance(t, DocToken)}
    if r_docs & w_docs:
        return True

    r_idx = {(t.table, t.field, _freeze(t.value)) for t in rset if isinstance(t, IndexToken)}
    w_idx = {(t.table, t.field, _freeze(t.value)) for t in wset if isinstance(t, IndexToken)}
    if r_idx & w_idx:
        return True

    return False


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze(v) for v in value))
    return value


def token_to_dict(token: Token) -> dict[str, Any]:
    return token.to_dict()
