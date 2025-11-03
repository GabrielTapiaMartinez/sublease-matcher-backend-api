from __future__ import annotations


class NotFoundError(Exception):
    """Requested resource does not exist."""


class ConflictError(Exception):
    """Invariant or uniqueness violation."""


class ForbiddenError(Exception):
    """Caller not allowed to perform the action."""


class ValidationError(Exception):
    """Input failed domain validation."""
