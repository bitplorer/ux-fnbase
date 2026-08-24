"""Fail-closed Intent door. Channel-shaped, without importing ux_channel.

Unknown names, illegal identifiers, and unregistered verbs are rejected.
Silent no-ops are forbidden.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

_ACTION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IntentError(Exception):
    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.status = int(status)


def collect_actions(instances: Mapping[str, Any] | Iterable[Any]) -> frozenset[str]:
    names: set[str] = set()
    if isinstance(instances, Mapping):
        items = instances.items()
    else:
        items = ((getattr(inst, "id", ""), inst) for inst in instances)
    for sid, inst in items:
        if not isinstance(sid, str) or not _IDENT.match(sid):
            continue
        for attr in dir(inst):
            if not _IDENT.match(attr) or attr.startswith("_"):
                continue
            fn = getattr(type(inst), attr, None)
            if fn is None:
                fn = getattr(inst, attr, None)
            if callable(fn) and getattr(fn, "_ux_action", False):
                names.add(f"{sid}.{attr}")
    return frozenset(names)


def require_action(name: str, allowed: frozenset[str]) -> str:
    if not isinstance(name, str) or not _ACTION.match(name):
        raise IntentError("illegal action name", status=400)
    if name not in allowed:
        raise IntentError("unknown action", status=404)
    return name
