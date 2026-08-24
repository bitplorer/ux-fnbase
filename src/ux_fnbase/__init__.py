"""ux-fnbase — fail-closed reactive function database (pure Python)."""

from ux_fnbase.errors import (
    DocumentNotFoundError,
    DurabilityError,
    FunctionExistsError,
    FunctionNotFoundError,
    UxFnbaseError,
    LimitExceededError,
    NestedTransactionError,
    PhaseError,
    SchemaViolationError,
    StoreClosedError,
    TableExistsError,
    TableNotFoundError,
)
from ux_fnbase.ids import new_id
from ux_fnbase.schema import TableSchema, integer, literal, string
from ux_fnbase.store import AtomicJsonBackend, QueryMeta, Store
from ux_fnbase.tokens import DocToken, IndexToken, ScanToken, intersects

__all__ = [
    "AtomicJsonBackend",
    "DocToken",
    "DocumentNotFoundError",
    "DurabilityError",
    "FunctionExistsError",
    "FunctionNotFoundError",
    "UxFnbaseError",
    "IndexToken",
    "LimitExceededError",
    "NestedTransactionError",
    "PhaseError",
    "QueryMeta",
    "ScanToken",
    "SchemaViolationError",
    "Store",
    "StoreClosedError",
    "TableExistsError",
    "TableNotFoundError",
    "TableSchema",
    "integer",
    "intersects",
    "literal",
    "new_id",
    "string",
]

__version__ = "0.1.0"
