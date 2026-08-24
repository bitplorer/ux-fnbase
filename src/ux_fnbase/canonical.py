"""Canonical JSON for deterministic equality and stable cache keys."""

from __future__ import annotations

import json
from typing import Any

RESERVED = frozenset({"_id", "_creationTime", "_generation"})


def canonical(value: Any) -> str:
    """Stable serialization: sorted keys, no whitespace, strict types."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=_default)


def loads_strict(text: str) -> Any:
    return json.loads(text)


def _default(obj: Any) -> Any:
    raise TypeError(f"non-canonical type: {type(obj)!r}")
