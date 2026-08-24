"""Composition root. Only module that sees both ux-fnbase and the wire.

Residuals closed
----------------
* HOST.view() takes a single locked snapshot of board+stats for one render.
* reset uses live.begin_reset (no early wake) then bind+publish once.
* Product Components import HOST, never ux_fnbase.Store.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

from playground.demo import STATUSES, create_demo_store
from playground.wire import LivePush, MutationDoor, QueryBinding, QueryState, bind_query

OnTick = Callable[[], None]


class PlaygroundHost:
    def __init__(self) -> None:
        self.live = LivePush()
        self.store = None
        self.door: MutationDoor | None = None
        self.board = QueryState(name="board")
        self.stats = QueryState(name="stats")
        self._bindings: list[QueryBinding] = []
        self._ticks: list[OnTick] = []
        self._view_lock = threading.Lock()
        self.reset()

    @property
    def fanout(self) -> LivePush:
        return self.live

    def on_tick(self, fn: OnTick) -> None:
        self._ticks.append(fn)

    def clear_ticks(self) -> None:
        self._ticks.clear()

    def _tick(self) -> None:
        for fn in list(self._ticks):
            try:
                fn()
            except Exception:
                continue

    def _on_board(self, state: QueryState) -> None:
        with self._view_lock:
            self.board = state.snapshot()
        self._tick()

    def _on_stats(self, state: QueryState) -> None:
        with self._view_lock:
            self.stats = state.snapshot()
        self._tick()

    def view(self) -> dict[str, Any]:
        """Consistent board + stats for one render. Closes split-generation residual."""
        with self._view_lock:
            board = self.board.snapshot()
            stats = self.stats.snapshot()
        return {
            "board": board,
            "stats": stats,
            "runtime": self.runtime(),
            "journal": self.journal(),
            "explain": self.explain_board(),
            "seq": self.live.seq,
        }

    def reset(self) -> PlaygroundHost:
        for binding in self._bindings:
            binding.detach()
        self._bindings.clear()
        if self.store is not None:
            try:
                self.store.close()
            except Exception:
                pass
        self.live.begin_reset()  # no notify — store not ready
        self.store = create_demo_store()
        self.door = MutationDoor(self.store)
        self._bindings = [
            bind_query(self.store, "board", on_change=self._on_board, fanout=self.live),
            bind_query(self.store, "stats", on_change=self._on_stats, fanout=self.live),
        ]
        # One publish after bind — seq advances once for the new generation
        self.live.publish(int(self.store.generation))
        return self

    def mutate(self, name: str, args: dict[str, Any] | None = None) -> Any:
        if self.door is None:
            raise RuntimeError("host has no mutation door")
        return self.door.run(name, args)

    def chaos(self, n: int = 6) -> int:
        import random

        docs = self.store.snapshot_documents("tasks") if self.store is not None else []
        moved = 0
        if not docs:
            return 0
        for _ in range(max(0, int(n))):
            pick = random.choice(docs)
            nxt = random.choice(STATUSES)
            try:
                self.mutate("move_task", {"id": pick["_id"], "status": nxt})
                moved += 1
            except Exception:
                continue
            docs = self.store.snapshot_documents("tasks") if self.store is not None else docs
        return moved

    def journal(self) -> list[Any]:
        if self.store is None:
            return []
        return self.store.journal()

    def explain_board(self) -> dict[str, Any]:
        if self.store is None:
            return {"read_set": [], "generation": 0}
        return self.store.explain("board")

    def runtime(self) -> dict[str, Any]:
        if self.store is None:
            return {"generation": 0, "subscriptions": 0, "tables": {}, "seq": self.live.seq}
        stats = self.store.stats()
        stats["seq"] = self.live.seq
        return stats


HOST = PlaygroundHost()
