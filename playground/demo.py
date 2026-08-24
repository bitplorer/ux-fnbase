"""Demo ux-fnbase schema, queries, and mutations. Imports ux-fnbase only."""

from __future__ import annotations

from typing import Any

from ux_fnbase import Store, TableSchema, literal, string

STATUSES = ("backlog", "doing", "done")


def _sort_docs(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(docs, key=lambda d: (int(d.get("_creationTime") or 0), str(d.get("_id") or "")))


def create_demo_store() -> Store:
    store = Store()
    store.define_table(
        "tasks",
        indexes=("status", "author"),
        schema=TableSchema(
            {
                "title": string(min_len=1, max_len=80),
                "status": literal(*STATUSES),
                "author": string(min_len=1, max_len=32),
                "note": string(min_len=0, max_len=160),
            }
        ),
    )

    @store.query
    def board(ctx):
        all_docs = _sort_docs(ctx.db.table("tasks").scan().collect())

        def by(status: str) -> list[dict[str, Any]]:
            return [d for d in all_docs if d.get("status") == status]

        return {
            "backlog": by("backlog"),
            "doing": by("doing"),
            "done": by("done"),
        }

    @store.query
    def by_status(ctx, status: str = "backlog"):
        return _sort_docs(ctx.db.table("tasks").index("status").eq(status).collect())

    @store.query
    def stats(ctx):
        all_docs = ctx.db.table("tasks").scan().collect()
        return {
            "total": len(all_docs),
            "backlog": sum(1 for d in all_docs if d.get("status") == "backlog"),
            "doing": sum(1 for d in all_docs if d.get("status") == "doing"),
            "done": sum(1 for d in all_docs if d.get("status") == "done"),
        }

    @store.mutation
    def seed(ctx):
        ctx.db.table("tasks").insert(
            {
                "title": "Define the read-set protocol",
                "status": "done",
                "author": "north",
                "note": "Document tokens. Never under-invalidate.",
            }
        )
        ctx.db.table("tasks").insert(
            {
                "title": "Single-writer serializable tx",
                "status": "doing",
                "author": "south",
                "note": "Exclusive lock, snapshot queries.",
            }
        )
        ctx.db.table("tasks").insert(
            {
                "title": "Fail-closed nested mutations",
                "status": "backlog",
                "author": "north",
                "note": "Subscribers cannot re-enter the write phase.",
            }
        )
        return True

    @store.mutation
    def add_task(ctx, title: str, author: str = "north", note: str = ""):
        return ctx.db.table("tasks").insert(
            {
                "title": str(title).strip(),
                "status": "backlog",
                "author": str(author or "north"),
                "note": str(note or ""),
            }
        )

    @store.mutation
    def move_task(ctx, id: str, status: str):
        return ctx.db.table("tasks").patch(str(id), {"status": str(status)})

    @store.mutation
    def remove_task(ctx, id: str):
        ctx.db.table("tasks").delete(str(id))
        return True

    store.run_mutation("seed")
    return store
