"""Thin ux-fnbase ↔ compose adapter. ux-fnbase never imports this package."""

from playground.wire.bind import (
    GenerationFanout,
    MutationDoor,
    QueryBinding,
    QueryState,
    bind_query,
)
from playground.wire.intent import IntentError, collect_actions, require_action
from playground.wire.live import LivePush, MorphOp

__all__ = [
    "GenerationFanout",
    "IntentError",
    "LivePush",
    "MorphOp",
    "MutationDoor",
    "QueryBinding",
    "QueryState",
    "bind_query",
    "collect_actions",
    "require_action",
]
