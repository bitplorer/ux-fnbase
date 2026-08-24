"""ux-fnbase ↔ compose wire.

Isolation Law
-------------
Imports ux-fnbase only. Does not import ux_compose, MorphState, Caps, or Channel.

* QueryBinding: subscribe → QueryState
* MutationDoor: sole path into Store.run_mutation
* GenerationFanout: ux-fnbase generation clock (legacy)
"""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ux_fnbase import SchemaViolationError, Store
from ux_fnbase.store import QueryMeta

OnChange = Callable[["QueryState"], None]


@dataclass
class QueryState:
    """Last legal result of a subscribed query. Not MorphState."""

    result: Any = None
    generation: int = 0
    name: str = ""
    elapsed_ms: float = 0.0
    read_set: tuple[Any, ...] = ()
    error: str | None = None

    def snapshot(self) -> "QueryState":
        return QueryState(
            result=copy.deepcopy(self.result),
            generation=self.generation,
            name=self.name,
            elapsed_ms=self.elapsed_ms,
            read_set=self.read_set,
            error=self.error,
        )


class MutationDoor:
    """Exclusive write door. Product code mutates ux-fnbase only through this type."""

    def __init__(self, store: Store) -> None:
        self._store = store

    def run(self, name: str, args: dict[str, Any] | None = None) -> Any:
        if not isinstance(name, str) or not name:
            raise SchemaViolationError("mutation name required")
        if args is not None and not isinstance(args, dict):
            raise SchemaViolationError("mutation args must be a dict or None")
        return self._store.run_mutation(name, args)

    def query(self, name: str, args: dict[str, Any] | None = None) -> Any:
        return self._store.run_query(name, args)


class GenerationFanout:
    """Monotonic ux-fnbase-generation clock. Never starts a mutation."""

    def __init__(self) -> None:
        self._cv = threading.Condition()
        self._generation = 0
        self._closed = False

    @property
    def generation(self) -> int:
        with self._cv:
            return self._generation

    def publish(self, generation: int) -> None:
        if not isinstance(generation, int) or generation < 0:
            return
        with self._cv:
            if self._closed:
                return
            if generation <= self._generation:
                return
            self._generation = generation
            self._cv.notify_all()

    def wait_after(self, seen: int, timeout: float = 15.0) -> int:
        with self._cv:
            if self._closed:
                return self._generation
            if self._generation > seen:
                return self._generation
            self._cv.wait(timeout=max(0.05, float(timeout)))
            return self._generation

    def close(self) -> None:
        with self._cv:
            self._closed = True
            self._cv.notify_all()

    def reopen(self) -> None:
        with self._cv:
            self._closed = False
            self._generation = 0
            self._cv.notify_all()


class QueryBinding:
    """Subscribe store.query(name) into QueryState.

    on_change must not call MutationDoor.run (notify phase → NestedTransactionError).
    """

    def __init__(
        self,
        store: Store,
        name: str,
        args: dict[str, Any] | None = None,
        *,
        on_change: OnChange | None = None,
        fanout: Any | None = None,
    ) -> None:
        if not isinstance(name, str) or not name:
            raise SchemaViolationError("query name required")
        self._store = store
        self._name = name
        self._args = copy.deepcopy(args) if args is not None else None
        self._on_change = on_change
        self._fanout = fanout
        self._unsub: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()
        self.state = QueryState(name=name)

    @property
    def attached(self) -> bool:
        return self._unsub is not None

    def attach(self) -> "QueryBinding":
        with self._lock:
            if self._unsub is not None:
                self._unsub()
                self._unsub = None
            self._unsub = self._store.subscribe(self._name, self._args, self._on_result)
        return self

    def detach(self) -> None:
        with self._lock:
            unsub = self._unsub
            self._unsub = None
        if unsub is not None:
            unsub()

    def _on_result(self, result: Any, meta: QueryMeta) -> None:
        self.state.result = copy.deepcopy(result)
        self.state.generation = int(meta.generation)
        self.state.name = meta.name
        self.state.elapsed_ms = float(meta.elapsed_ms)
        self.state.read_set = tuple(meta.read_set)
        self.state.error = None
        if self._fanout is not None:
            # Equal-gen publish is a no-op on LivePush/GenerationFanout
            self._fanout.publish(int(meta.generation))
        cb = self._on_change
        if cb is not None:
            cb(self.state)


def bind_query(
    store: Store,
    name: str,
    args: dict[str, Any] | None = None,
    *,
    on_change: OnChange | None = None,
    fanout: Any | None = None,
) -> QueryBinding:
    return QueryBinding(store, name, args, on_change=on_change, fanout=fanout).attach()
