"""Table schema validators. Fail closed on type / length / literal mismatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ux_fnbase.errors import SchemaViolationError


Validator = Callable[[Any], Any]


def string(*, min_len: int = 0, max_len: int = 10_000) -> Validator:
    def _v(value: Any) -> str:
        if not isinstance(value, str):
            raise SchemaViolationError(f"expected string, got {type(value).__name__}")
        if len(value) < min_len or len(value) > max_len:
            raise SchemaViolationError(f"string length {len(value)} outside [{min_len}, {max_len}]")
        return value

    return _v


def literal(*allowed: Any) -> Validator:
    allow = frozenset(allowed)

    def _v(value: Any) -> Any:
        if value not in allow:
            raise SchemaViolationError(f"value {value!r} not in {sorted(allow)!r}")
        return value

    return _v


def integer(*, min_v: int | None = None, max_v: int | None = None) -> Validator:
    def _v(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise SchemaViolationError(f"expected int, got {type(value).__name__}")
        if min_v is not None and value < min_v:
            raise SchemaViolationError(f"int {value} < {min_v}")
        if max_v is not None and value > max_v:
            raise SchemaViolationError(f"int {value} > {max_v}")
        return value

    return _v


@dataclass(frozen=True, slots=True)
class TableSchema:
    fields: dict[str, Validator]

    def validate(self, doc: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        if not isinstance(doc, dict):
            raise SchemaViolationError("document must be a dict")
        out: dict[str, Any] = {}
        if partial:
            for k, v in doc.items():
                if k.startswith("_"):
                    continue
                if k not in self.fields:
                    raise SchemaViolationError(f"unknown field {k!r}")
                out[k] = self.fields[k](v)
            return out
        for name, validator in self.fields.items():
            if name not in doc:
                raise SchemaViolationError(f"missing field {name!r}")
            out[name] = validator(doc[name])
        for k in doc:
            if k.startswith("_"):
                continue
            if k not in self.fields:
                raise SchemaViolationError(f"unknown field {k!r}")
        return out
