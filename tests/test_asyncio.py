"""Async wrappers preserve sync store semantics."""

from __future__ import annotations

import asyncio

import pytest

from ux_fnbase import Store, TableSchema, string
from ux_fnbase.asyncio import explain, run_mutation, run_query, subscribe_once


def _store() -> Store:
    store = Store()
    store.define_table(
        "items",
        schema=TableSchema({"title": string(min_len=1, max_len=40)}),
    )

    @store.query
    def all_items(ctx):
        return ctx.db.table("items").scan().collect()

    @store.mutation
    def add(ctx, title: str):
        return ctx.db.table("items").insert({"title": title})

    return store


def test_async_run_query_and_mutation():
    store = _store()

    async def body():
        await run_mutation(store, "add", {"title": "async"})
        rows = await run_query(store, "all_items")
        assert len(rows) == 1
        meta = await explain(store, "all_items")
        assert meta["generation"] == store.generation
        return rows

    asyncio.run(body())
    store.close()


def test_subscribe_once_immediate():
    store = _store()
    store.run_mutation("add", {"title": "seed"})

    async def body():
        result, meta = await subscribe_once(store, "all_items", timeout=2.0)
        assert len(result) == 1
        assert meta.generation == store.generation

    asyncio.run(body())
    store.close()
