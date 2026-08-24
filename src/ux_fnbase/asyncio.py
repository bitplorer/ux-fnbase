"""Optional asyncio wrappers around the sync Store.

These helpers never change Store guarantees. They only move blocking
``run_query`` / ``run_mutation`` / one-shot subscribe reads onto the
default executor via ``asyncio.to_thread``.

The Store remains single-writer and phase-checked on the worker thread.
Do not call these wrappers from inside a query or mutation body.

Example
-------
::

    store = Store()
    ...
    result = await run_query(store, "board")
    await run_mutation(store, "add", {"title": "x"})
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from ux_fnbase.store import QueryMeta, Store

__all__ = [
    "run_query",
    "run_mutation",
    "explain",
    "subscribe_once",
]


async def run_query(store: Store, name: str, args: Any = None) -> Any:
    """Async wrapper for ``Store.run_query``."""
    return await asyncio.to_thread(store.run_query, name, args)


async def run_mutation(store: Store, name: str, args: Any = None) -> Any:
    """Async wrapper for ``Store.run_mutation``."""
    return await asyncio.to_thread(store.run_mutation, name, args)


async def explain(store: Store, name: str, args: Any = None) -> dict[str, Any]:
    """Async wrapper for ``Store.explain``."""
    return await asyncio.to_thread(store.explain, name, args)


async def subscribe_once(
    store: Store,
    name: str,
    args: Any = None,
    *,
    timeout: float = 5.0,
) -> tuple[Any, QueryMeta]:
    """Wait until the named query produces a delivery, then unsubscribe.

    Useful for tests and one-shot async waits. For long-lived subscriptions,
    use ``Store.subscribe`` on a dedicated thread or bridge with a queue.
    """

    loop = asyncio.get_running_loop()
    future: asyncio.Future[tuple[Any, QueryMeta]] = loop.create_future()
    unsub_holder: list[Callable[[], None]] = []

    def callback(result: Any, meta: QueryMeta) -> None:
        if not future.done():
            loop.call_soon_threadsafe(future.set_result, (result, meta))

    def attach() -> None:
        unsub_holder.append(store.subscribe(name, args, callback))

    await asyncio.to_thread(attach)
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        if unsub_holder:
            unsub = unsub_holder[0]

            def _detach() -> None:
                unsub()

            await asyncio.to_thread(_detach)
