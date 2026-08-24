"""Channel-shaped live push. Never imports ux_channel. Never starts a mutation.

Residuals closed
----------------
* seq is monotonic and survives ux-fnbase generation reset (Last-Event-ID safe).
* begin_reset clears morph cache without waking waiters (store not ready).
* publish(generation) no-ops on equal gen → no double-seq from board+stats.
* publish_morph rejects stale generation (never overwrites newer HTML).
* wait_morph_at_least bridges notify-clock → HTTP-render race.

Wire shape matches compose ops_to_wire morph ops::

    {"op": "morph", "target": "#stage", "html": "...", "generation": N, "seq": S}

References
----------
* Isolation Law — ux-compose docs/FLOW.md
* SSE Last-Event-ID — HTML Living Standard, Server-sent events
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Optional

MAX_MORPH_CHARS = 1_000_000


@dataclass(frozen=True, slots=True)
class MorphOp:
    op: str
    target: str
    html: str
    generation: int
    seq: int

    def to_wire(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "target": self.target,
            "html": self.html,
            "generation": self.generation,
            "seq": self.seq,
        }


def _norm_target(target: str) -> str:
    t = str(target or "").strip()
    if not t:
        return "#stage"
    if not t.startswith(("#", "[")):
        t = f"#{t}"
    return t


class LivePush:
    """Monotonic morph fanout — Channel analogue without importing Channel."""

    def __init__(self) -> None:
        self._cv = threading.Condition()
        self._generation = 0  # ux-fnbase generation (may restart)
        self._seq = 0  # Monotonic; never decreases
        self._closed = False
        self._ops: dict[str, MorphOp] = {}

    @property
    def generation(self) -> int:
        with self._cv:
            return self._generation

    @property
    def seq(self) -> int:
        with self._cv:
            return self._seq

    def publish(self, generation: int) -> None:
        """ux-fnbase clock from QueryBinding during notify. HTML is not here."""
        if not isinstance(generation, int) or generation < 0:
            return
        with self._cv:
            if self._closed:
                return
            if generation <= self._generation:
                return  # equal-gen no-op closes double-publish residual
            self._generation = generation
            self._seq += 1
            self._cv.notify_all()

    def publish_morph(self, target: str, generation: int, html: str) -> MorphOp:
        """HTTP door after a legal render. Never from ux-fnbase notify."""
        if not isinstance(generation, int) or generation < 0:
            generation = 0
        target = _norm_target(target)
        text = html if isinstance(html, str) else ""
        kind = "morph"
        if len(text) > MAX_MORPH_CHARS:
            text = ""
            kind = "tick"
        with self._cv:
            existing = self._ops.get(target)
            if existing is not None and existing.generation > generation:
                return existing  # reject stale
            op = MorphOp(
                op=kind,
                target=target,
                html=text,
                generation=generation,
                seq=self._seq,
            )
            self._ops[target] = op
            self._cv.notify_all()
            return op

    def latest(self, target: str = "#stage") -> Optional[MorphOp]:
        target = _norm_target(target)
        with self._cv:
            return self._ops.get(target)

    def wait_after(self, seen_seq: int, timeout: float = 15.0) -> int:
        """Block until seq advances past seen_seq. Returns current seq."""
        with self._cv:
            if self._closed:
                return self._seq
            if self._seq > seen_seq:
                return self._seq
            self._cv.wait(timeout=max(0.05, float(timeout)))
            return self._seq

    def wait_morph_at_least(
        self,
        generation: int,
        *,
        target: str = "#stage",
        timeout: float = 0.35,
    ) -> Optional[MorphOp]:
        """Bridge notify-clock → HTTP-render race without a second client pull."""
        target = _norm_target(target)
        with self._cv:
            if self._closed:
                return self._ops.get(target)
            op = self._ops.get(target)
            if op is not None and op.generation >= generation:
                return op
            self._cv.wait(timeout=max(0.0, float(timeout)))
            return self._ops.get(target)

    def begin_reset(self) -> None:
        """Drop morphs and ux-fnbase clock. Do not wake waiters (store not ready)."""
        with self._cv:
            self._generation = 0
            self._ops.clear()
            # seq unchanged — waiters stay on old seen until publish after bind

    def close(self) -> None:
        with self._cv:
            self._closed = True
            self._cv.notify_all()

    def reopen(self) -> None:
        with self._cv:
            self._closed = False
            self._generation = 0
            self._ops.clear()
            self._seq += 1
            self._cv.notify_all()
