"""ux-fnbase error types. Fail closed — never swallow."""

from __future__ import annotations


class UxFnbaseError(Exception):
    """Base error for the store."""


class PhaseError(UxFnbaseError):
    """Operation not allowed in the current phase."""


class NestedTransactionError(UxFnbaseError):
    """Mutation attempted while already inside a transaction or notify."""


class SchemaViolationError(UxFnbaseError):
    """Document or args failed schema validation."""


class FunctionNotFoundError(UxFnbaseError):
    """Named query or mutation is not registered."""


class FunctionExistsError(UxFnbaseError):
    """Duplicate registration of a query or mutation name."""


class TableNotFoundError(UxFnbaseError):
    """Table does not exist."""


class TableExistsError(UxFnbaseError):
    """Table already defined with conflicting indexes."""


class DocumentNotFoundError(UxFnbaseError):
    """Document id not present in the table."""


class StoreClosedError(UxFnbaseError):
    """Store has been closed."""


class DurabilityError(UxFnbaseError):
    """Persist failed; in-memory state rolled back."""


class LimitExceededError(UxFnbaseError):
    """Hard resource limit hit (docs, writes, subscriptions, payload)."""
