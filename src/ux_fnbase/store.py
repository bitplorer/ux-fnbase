"""ux-fnbase store: single-writer serializable transactions, snapshot queries, read-set invalidation.

Concurrency model
-----------------
* Exactly one mutation may run at a time (exclusive write lock).
* Queries capture an immutable snapshot under the lock, then run lock-free.
* Nested mutations, writes from queries, and mutations from subscriber
  callbacks are rejected (NestedTransactionError / PhaseError).
* A thrown mutation discards its working copy; generation does not advance.
* Durable backends persist *before* the snapshot is published.

Isolation
---------
Mutations are serializable (single writer). Queries have snapshot isolation
relative to the last committed generation — never dirty reads.

References
----------
* ANSI SQL isolation phenomena — Berenson et al., 1995
* Snapshot isolation — Adya, 1999; PostgreSQL MVCC
* Fine-grained reactive invalidation — SolidJS; Convex query subscriptions
* Atomic file replace — POSIX rename(2) on the same filesystem
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ux_fnbase.canonical import canonical
from ux_fnbase.errors import (
    DocumentNotFoundError,
    DurabilityError,
    FunctionExistsError,
    FunctionNotFoundError,
    LimitExceededError,
    NestedTransactionError,
    PhaseError,
    SchemaViolationError,
    StoreClosedError,
    TableExistsError,
    TableNotFoundError,
)
from ux_fnbase.ids import new_id
from ux_fnbase.schema import TableSchema
from ux_fnbase.tokens import DocToken, IndexToken, ScanToken, Token, intersects, token_to_dict

MAX_DOC_BYTES = 256_000
MAX_DOCS_PER_TABLE = 100_000
MAX_TX_WRITES = 10_000
MAX_QUERY_RESULTS = 10_000
MAX_SUBSCRIPTIONS = 10_000
MAX_JOURNAL = 256
WRITE_LOCK_TIMEOUT_S = 30.0

Phase = str  # idle | query | mutation | notify

_phase: ContextVar[Phase] = ContextVar("ux_fnbase_phase", default="idle")
_read_buf: ContextVar[list[Token] | None] = ContextVar("ux_fnbase_reads", default=None)
_write_ctx: ContextVar["MutationSession | None"] = ContextVar("ux_fnbase_writes", default=None)


def _require_phase(*allowed: Phase) -> Phase:
    current = _phase.get()
    if current not in allowed:
        raise PhaseError(f"operation not allowed during phase {current!r}")
    return current


@dataclass(frozen=True, slots=True)
class QueryMeta:
    name: str
    generation: int
    elapsed_ms: float
    read_set: tuple[Any, ...]


@dataclass
class JournalEntry:
    generation: int
    name: str
    ok: bool
    elapsed_ms: float
    error: str | None = None


@dataclass
class _Table:
    name: str
    indexes: tuple[str, ...]
    schema: TableSchema | None
    docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    # index field -> value_key -> set of ids
    index_map: dict[str, dict[str, set[str]]] = field(default_factory=dict)

    def clone(self) -> "_Table":
        t = _Table(
            name=self.name,
            indexes=self.indexes,
            schema=self.schema,
            docs=copy.deepcopy(self.docs),
            index_map={f: {k: set(ids) for k, ids in m.items()} for f, m in self.index_map.items()},
        )
        return t


@dataclass(frozen=True, slots=True)
class Snapshot:
    generation: int
    tables: dict[str, _Table]


class MutationSession:
    def __init__(self, store: "Store") -> None:
        self.store = store
        self.writes: list[Token] = []
        self.write_count = 0
        # Working copy of tables (lazy clone on first write per table)
        self.working: dict[str, _Table] = {}
        self.touched: set[str] = set()

    def table(self, name: str) -> "MutationTable":
        return MutationTable(self, name)

    def _ensure(self, name: str) -> _Table:
        if name not in self.working:
            base = self.store._tables.get(name)
            if base is None:
                raise TableNotFoundError(name)
            self.working[name] = base.clone()
        self.touched.add(name)
        return self.working[name]


class MutationTable:
    def __init__(self, session: MutationSession, name: str) -> None:
        self._session = session
        self.name = name

    def insert(self, doc: dict[str, Any]) -> dict[str, Any]:
        _require_phase("mutation")
        session = self._session
        session.write_count += 1
        if session.write_count > MAX_TX_WRITES:
            raise LimitExceededError("MAX_TX_WRITES")
        table = session._ensure(self.name)
        data = dict(doc)
        if table.schema is not None:
            data = table.schema.validate(data)
        doc_id = new_id()
        now = int(time.time() * 1000)
        full = {
            **data,
            "_id": doc_id,
            "_creationTime": now,
            "_generation": session.store._generation + 1,
        }
        payload = canonical(full)
        if len(payload) > MAX_DOC_BYTES:
            raise LimitExceededError("MAX_DOC_BYTES")
        if len(table.docs) >= MAX_DOCS_PER_TABLE:
            raise LimitExceededError("MAX_DOCS_PER_TABLE")
        table.docs[doc_id] = full
        self._index_add(table, full)
        session.writes.append(DocToken(self.name, doc_id))
        for field in table.indexes:
            session.writes.append(IndexToken(self.name, field, full.get(field)))
        session.writes.append(ScanToken(self.name))
        return copy.deepcopy(full)

    def patch(self, doc_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        _require_phase("mutation")
        session = self._session
        session.write_count += 1
        if session.write_count > MAX_TX_WRITES:
            raise LimitExceededError("MAX_TX_WRITES")
        table = session._ensure(self.name)
        if doc_id not in table.docs:
            raise DocumentNotFoundError(doc_id)
        old = table.docs[doc_id]
        self._index_remove(table, old)
        data = {k: v for k, v in old.items() if not k.startswith("_")}
        data.update(patch)
        if table.schema is not None:
            validated = table.schema.validate(data)
        else:
            validated = data
        full = {
            **validated,
            "_id": doc_id,
            "_creationTime": old["_creationTime"],
            "_generation": session.store._generation + 1,
        }
        payload = canonical(full)
        if len(payload) > MAX_DOC_BYTES:
            raise LimitExceededError("MAX_DOC_BYTES")
        table.docs[doc_id] = full
        self._index_add(table, full)
        session.writes.append(DocToken(self.name, doc_id))
        for field in table.indexes:
            session.writes.append(IndexToken(self.name, field, old.get(field)))
            session.writes.append(IndexToken(self.name, field, full.get(field)))
        session.writes.append(ScanToken(self.name))
        return copy.deepcopy(full)

    def delete(self, doc_id: str) -> None:
        _require_phase("mutation")
        session = self._session
        session.write_count += 1
        if session.write_count > MAX_TX_WRITES:
            raise LimitExceededError("MAX_TX_WRITES")
        table = session._ensure(self.name)
        if doc_id not in table.docs:
            raise DocumentNotFoundError(doc_id)
        old = table.docs.pop(doc_id)
        self._index_remove(table, old)
        session.writes.append(DocToken(self.name, doc_id))
        for field in table.indexes:
            session.writes.append(IndexToken(self.name, field, old.get(field)))
        session.writes.append(ScanToken(self.name))

    def _index_add(self, table: _Table, doc: dict[str, Any]) -> None:
        for field in table.indexes:
            key = canonical(doc.get(field))
            table.index_map.setdefault(field, {}).setdefault(key, set()).add(doc["_id"])

    def _index_remove(self, table: _Table, doc: dict[str, Any]) -> None:
        for field in table.indexes:
            key = canonical(doc.get(field))
            ids = table.index_map.get(field, {}).get(key)
            if ids is not None:
                ids.discard(doc["_id"])
                if not ids:
                    table.index_map[field].pop(key, None)


class QueryDb:
    def __init__(self, snapshot: Snapshot) -> None:
        self._snapshot = snapshot

    def table(self, name: str) -> "QueryTable":
        if name not in self._snapshot.tables:
            raise TableNotFoundError(name)
        return QueryTable(self._snapshot.tables[name])


class QueryTable:
    def __init__(self, table: _Table) -> None:
        self._table = table

    def get(self, doc_id: str) -> dict[str, Any] | None:
        _require_phase("query", "idle", "notify")
        buf = _read_buf.get()
        if buf is not None:
            buf.append(DocToken(self._table.name, doc_id))
        doc = self._table.docs.get(doc_id)
        return copy.deepcopy(doc) if doc else None

    def scan(self) -> "QueryCursor":
        _require_phase("query", "idle", "notify")
        buf = _read_buf.get()
        if buf is not None:
            buf.append(ScanToken(self._table.name))
        return QueryCursor(self._table, list(self._table.docs.values()))

    def index(self, field: str) -> "IndexQuery":
        if field not in self._table.indexes:
            raise SchemaViolationError(f"no index on {field!r}")
        return IndexQuery(self._table, field)


class IndexQuery:
    def __init__(self, table: _Table, field: str) -> None:
        self._table = table
        self._field = field

    def eq(self, value: Any) -> "QueryCursor":
        _require_phase("query", "idle", "notify")
        buf = _read_buf.get()
        if buf is not None:
            buf.append(IndexToken(self._table.name, self._field, value))
        key = canonical(value)
        ids = self._table.index_map.get(self._field, {}).get(key, set())
        docs = [self._table.docs[i] for i in ids if i in self._table.docs]
        return QueryCursor(self._table, docs)


class QueryCursor:
    def __init__(self, table: _Table, docs: list[dict[str, Any]]) -> None:
        self._docs = docs

    def collect(self) -> list[dict[str, Any]]:
        if len(self._docs) > MAX_QUERY_RESULTS:
            raise LimitExceededError("MAX_QUERY_RESULTS")
        return copy.deepcopy(self._docs)


class QueryContext:
    def __init__(self, snapshot: Snapshot) -> None:
        self.db = QueryDb(snapshot)


class MutationContext:
    def __init__(self, session: MutationSession) -> None:
        self.db = session


class AtomicJsonBackend:
    """Persist snapshot via temp file + os.replace (atomic on same filesystem)."""

    def __init__(self, path: str) -> None:
        self.path = path

    def save(self, payload: dict[str, Any]) -> None:
        directory = os.path.dirname(os.path.abspath(self.path)) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".ux_fnbase-", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, sort_keys=True, separators=(",", ":"))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except Exception as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise DurabilityError(str(exc)) from exc

    def load(self) -> dict[str, Any] | None:
        if not os.path.exists(self.path):
            return None
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)


@dataclass
class _Sub:
    name: str
    args_key: str
    args: Any
    callback: Callable[[Any, QueryMeta], None]
    last_canonical: str | None = None


class Store:
    def __init__(self, backend: AtomicJsonBackend | None = None) -> None:
        self._lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._tables: dict[str, _Table] = {}
        self._queries: dict[str, Callable] = {}
        self._mutations: dict[str, Callable] = {}
        self._generation = 0
        self._subs: dict[int, _Sub] = {}
        self._sub_seq = 0
        self._journal: list[JournalEntry] = []
        self._backend = backend
        self._closed = False
        if backend is not None:
            self._boot_from_backend()

    # ----- schema -----------------------------------------------------------

    def define_table(
        self,
        name: str,
        *,
        indexes: tuple[str, ...] | list[str] = (),
        schema: TableSchema | None = None,
    ) -> None:
        with self._lock:
            self._ensure_open()
            idx = tuple(indexes)
            if name in self._tables:
                existing = self._tables[name]
                if existing.indexes == idx and existing.schema == schema:
                    return  # idempotent
                raise TableExistsError(name)
            self._tables[name] = _Table(name=name, indexes=idx, schema=schema)

    def query(self, fn: Callable | None = None, *, name: str | None = None):
        def register(f: Callable) -> Callable:
            qname = name or f.__name__
            if qname in self._queries:
                raise FunctionExistsError(qname)
            self._queries[qname] = f
            return f

        if fn is not None:
            return register(fn)
        return register

    def mutation(self, fn: Callable | None = None, *, name: str | None = None):
        def register(f: Callable) -> Callable:
            mname = name or f.__name__
            if mname in self._mutations:
                raise FunctionExistsError(mname)
            self._mutations[mname] = f
            return f

        if fn is not None:
            return register(fn)
        return register

    # ----- runtime ----------------------------------------------------------

    @property
    def generation(self) -> int:
        return self._generation

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._subs.clear()

    def _ensure_open(self) -> None:
        if self._closed:
            raise StoreClosedError("store closed")

    def _capture_snapshot(self) -> Snapshot:
        tables = {n: t.clone() for n, t in self._tables.items()}
        return Snapshot(generation=self._generation, tables=tables)

    def run_query(self, name: str, args: Any = None) -> Any:
        result, _meta = self._run_query_inner(name, args)
        return result

    def explain(self, name: str, args: Any = None) -> dict[str, Any]:
        result, meta = self._run_query_inner(name, args)
        return {
            "result": result,
            "generation": meta.generation,
            "elapsed_ms": meta.elapsed_ms,
            "read_set": list(meta.read_set),
            "name": meta.name,
        }

    def _run_query_inner(self, name: str, args: Any = None) -> tuple[Any, QueryMeta]:
        self._ensure_open()
        if name not in self._queries:
            raise FunctionNotFoundError(name)
        phase = _phase.get()
        if phase == "mutation":
            raise PhaseError("queries cannot run during mutation phase")
        # Capture snapshot under lock
        with self._lock:
            snap = self._capture_snapshot()
        t0 = time.perf_counter()
        token = _phase.set("query")
        buf: list[Token] = []
        rtoken = _read_buf.set(buf)
        try:
            ctx = QueryContext(snap)
            fn = self._queries[name]
            if args is None:
                result = fn(ctx)
            elif isinstance(args, dict):
                result = fn(ctx, **args)
            else:
                result = fn(ctx, args)
        finally:
            _read_buf.reset(rtoken)
            _phase.reset(token)
        elapsed = (time.perf_counter() - t0) * 1000.0
        meta = QueryMeta(
            name=name,
            generation=snap.generation,
            elapsed_ms=elapsed,
            read_set=tuple(token_to_dict(t) for t in buf),
        )
        return result, meta

    def run_mutation(self, name: str, args: Any = None) -> Any:
        self._ensure_open()
        if name not in self._mutations:
            raise FunctionNotFoundError(name)
        if _phase.get() != "idle":
            raise NestedTransactionError(f"cannot nest mutation {name!r} during phase {_phase.get()!r}")
        if not self._write_lock.acquire(timeout=WRITE_LOCK_TIMEOUT_S):
            raise PhaseError("write lock timeout")
        t0 = time.perf_counter()
        session = MutationSession(self)
        ptoken = _phase.set("mutation")
        wtoken = _write_ctx.set(session)
        error: str | None = None
        ok = False
        result: Any = None
        try:
            fn = self._mutations[name]
            if args is None:
                result = fn(MutationContext(session))
            elif isinstance(args, dict):
                result = fn(MutationContext(session), **args)
            else:
                result = fn(MutationContext(session), args)
            # Commit under store lock with pre-images for fail-closed rollback
            with self._lock:
                pre_images = {n: self._tables[n] for n in session.touched}
                pre_gen = self._generation
                next_gen = pre_gen + 1
                for tname, table in session.working.items():
                    self._tables[tname] = table
                self._generation = next_gen
                if self._backend is not None:
                    try:
                        self._backend.save(self._serialize())
                    except Exception as exc:
                        for n, table in pre_images.items():
                            self._tables[n] = table
                        self._generation = pre_gen
                        raise DurabilityError(str(exc)) from exc
                write_set = frozenset(session.writes)
            ok = True
            self._notify(write_set)
        except DurabilityError:
            error = "durability"
            raise
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            _write_ctx.reset(wtoken)
            _phase.reset(ptoken)
            self._write_lock.release()
            elapsed = (time.perf_counter() - t0) * 1000.0
            with self._lock:
                self._journal.append(
                    JournalEntry(
                        generation=self._generation if ok else self._generation,
                        name=name,
                        ok=ok,
                        elapsed_ms=elapsed,
                        error=error,
                    )
                )
                if len(self._journal) > MAX_JOURNAL:
                    self._journal = self._journal[-MAX_JOURNAL:]
        return result

    def _notify(self, write_set: frozenset[Token]) -> None:
        token = _phase.set("notify")
        try:
            with self._lock:
                items = list(self._subs.items())
            dead: list[int] = []
            for sid, sub in items:
                try:
                    result, meta = self._run_query_inner(sub.name, sub.args)
                    reads = [
                        _dict_to_token(d) for d in meta.read_set if isinstance(d, dict)
                    ]
                    # No intersection → this sub is unaffected
                    if sub.last_canonical is not None and not intersects(reads, write_set):
                        continue
                    canon = canonical(result)
                    # Intersection but identical result → no residual callback
                    if sub.last_canonical is not None and canon == sub.last_canonical:
                        continue
                    sub.last_canonical = canon
                    sub.callback(result, meta)
                except Exception:
                    # Raising callback cancels *that* subscription only
                    dead.append(sid)
            if dead:
                with self._lock:
                    for sid in dead:
                        self._subs.pop(sid, None)
        finally:
            _phase.reset(token)

    def subscribe(
        self,
        name: str,
        args: Any,
        callback: Callable[[Any, QueryMeta], None],
    ) -> Callable[[], None]:
        self._ensure_open()
        if name not in self._queries:
            raise FunctionNotFoundError(name)
        with self._lock:
            if len(self._subs) >= MAX_SUBSCRIPTIONS:
                raise LimitExceededError("MAX_SUBSCRIPTIONS")
            self._sub_seq += 1
            sid = self._sub_seq
        # Immediate delivery in idle (not notify) so first paint works
        result, meta = self._run_query_inner(name, args)
        sub = _Sub(
            name=name,
            args_key=canonical(args),
            args=copy.deepcopy(args) if args is not None else None,
            callback=callback,
            last_canonical=canonical(result),
        )
        with self._lock:
            self._subs[sid] = sub
        try:
            callback(result, meta)
        except Exception:
            with self._lock:
                self._subs.pop(sid, None)
            raise

        def unsub() -> None:
            with self._lock:
                self._subs.pop(sid, None)

        return unsub

    def journal(self) -> list[JournalEntry]:
        with self._lock:
            return list(self._journal)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "generation": self._generation,
                "subscriptions": len(self._subs),
                "queries": list(self._queries.keys()),
                "mutations": list(self._mutations.keys()),
                "tables": {
                    n: {"docs": len(t.docs), "indexes": list(t.indexes)}
                    for n, t in self._tables.items()
                },
            }

    def snapshot_documents(self, table: str) -> list[dict[str, Any]]:
        with self._lock:
            t = self._tables.get(table)
            if t is None:
                return []
            return copy.deepcopy(list(t.docs.values()))

    def _serialize(self) -> dict[str, Any]:
        tables = {}
        for name, t in self._tables.items():
            tables[name] = {
                "indexes": list(t.indexes),
                "docs": list(t.docs.values()),
            }
        return {"generation": self._generation, "tables": tables}

    def _boot_from_backend(self) -> None:
        assert self._backend is not None
        payload = self._backend.load()
        if not payload:
            return
        self._generation = int(payload.get("generation", 0))
        for name, raw in (payload.get("tables") or {}).items():
            indexes = tuple(raw.get("indexes") or [])
            if name not in self._tables:
                self._tables[name] = _Table(name=name, indexes=indexes, schema=None)
            table = self._tables[name]
            for doc in raw.get("docs") or []:
                doc_id = doc["_id"]
                table.docs[doc_id] = doc
                for field in table.indexes:
                    key = canonical(doc.get(field))
                    table.index_map.setdefault(field, {}).setdefault(key, set()).add(doc_id)


def _dict_to_token(d: dict[str, Any]) -> Token:
    kind = d.get("kind")
    if kind == "doc":
        return DocToken(str(d["table"]), str(d["id"]))
    if kind == "index":
        return IndexToken(str(d["table"]), str(d["field"]), d.get("value"))
    return ScanToken(str(d["table"]))
