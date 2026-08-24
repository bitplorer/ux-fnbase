"""Prove residuals are closed: race, reset, equal-gen, intent, view snapshot."""

from __future__ import annotations

import threading
import time

import pytest

from ux_fnbase import NestedTransactionError
from playground.demo import create_demo_store
from playground.host import HOST
from playground.wire import (
    IntentError,
    LivePush,
    MutationDoor,
    bind_query,
    collect_actions,
    require_action,
)
from playground.wire.live import MorphOp


# --- LivePush residuals -----------------------------------------------------


def test_equal_generation_publish_is_noop():
    live = LivePush()
    live.publish(3)
    seq = live.seq
    live.publish(3)  # board + stats same gen
    assert live.seq == seq


def test_seq_survives_begin_reset():
    live = LivePush()
    live.publish(5)
    seq = live.seq
    live.begin_reset()
    assert live.generation == 0
    assert live.latest("#stage") is None
    assert live.seq == seq  # not woken, not decremented
    live.publish(1)
    assert live.seq == seq + 1


def test_stale_morph_rejected():
    live = LivePush()
    live.publish(4)
    first = live.publish_morph("#stage", 4, "<div>a</div>")
    second = live.publish_morph("#stage", 2, "<div>old</div>")
    assert second is first
    assert "a" in live.latest("#stage").html


def test_wait_morph_closes_notify_render_race():
    live = LivePush()
    live.publish(7)
    box: list[MorphOp | None] = []

    def waiter():
        box.append(live.wait_morph_at_least(7, timeout=1.0))

    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.05)
    live.publish_morph("#stage", 7, "<section id='stage'>ready</section>")
    t.join(timeout=2)
    assert box[0] is not None
    assert box[0].generation == 7
    assert "ready" in box[0].html


def test_oversized_morph_becomes_tick():
    live = LivePush()
    live.publish(1)
    op = live.publish_morph("#stage", 1, "x" * 1_000_008)
    assert op.op == "tick"
    assert op.html == ""


# --- Wire / notify residual -------------------------------------------------


def test_notify_callback_cannot_mutate():
    store = create_demo_store()
    door = MutationDoor(store)
    nested = []

    def boom(_state):
        try:
            door.run("add_task", {"title": "from notify", "author": "north"})
        except NestedTransactionError as exc:
            nested.append(exc)

    bind_query(store, "stats", on_change=boom)
    nested.clear()
    door.run("add_task", {"title": "second", "author": "north"})
    assert nested
    store.close()


def test_two_bindings_one_seq_bump():
    store = create_demo_store()
    live = LivePush()
    bind_query(store, "board", fanout=live)
    bind_query(store, "stats", fanout=live)
    seq_before = live.seq
    MutationDoor(store).run("add_task", {"title": "one bump", "author": "north"})
    # One generation advance → one seq bump even with two bindings
    assert live.seq == seq_before + 1
    store.close()


# --- Host view residual -----------------------------------------------------


def test_host_view_consistent_snapshot():
    HOST.reset()
    view = HOST.view()
    board = view["board"].result
    stats = view["stats"].result
    total = sum(len(board[k]) for k in ("backlog", "doing", "done"))
    assert total == stats["total"]
    assert "seq" in view


def test_host_reset_does_not_stall_seq():
    HOST.reset()
    seq0 = HOST.live.seq
    HOST.mutate("add_task", {"title": "before reset", "author": "north"})
    seq1 = HOST.live.seq
    assert seq1 > seq0
    HOST.reset()
    assert HOST.live.seq >= seq1  # begin_reset kept seq; publish may advance
    assert HOST.stats.result["total"] == 3


# --- Intent residual --------------------------------------------------------


def test_intent_fail_closed():
    allowed = frozenset({"stage.add"})
    assert require_action("stage.add", allowed) == "stage.add"
    with pytest.raises(IntentError) as e404:
        require_action("stage.nope", allowed)
    assert e404.value.status == 404
    with pytest.raises(IntentError) as e400:
        require_action("stage.add.extra", allowed)
    assert e400.value.status == 400


class _Fake:
    id = "stage"

    def add(self):
        pass

    add._ux_action = True  # type: ignore


def test_collect_actions_only_marked():
    names = collect_actions({"stage": _Fake()})
    assert "stage.add" in names
