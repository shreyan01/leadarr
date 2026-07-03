"""Application-level exceptions, mapped to HTTP responses in main.py."""
from __future__ import annotations


class LeadForgeError(Exception):
    """Base class for all domain errors."""

    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str, *, details: list[dict] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(LeadForgeError):
    code = "not_found"
    status_code = 404


class ValidationError(LeadForgeError):
    code = "validation_error"
    status_code = 422


class ConflictError(LeadForgeError):
    code = "conflict"
    status_code = 409


class ProviderError(LeadForgeError):
    """Raised when an external adapter (AI, discovery, email) fails."""

    code = "provider_error"
    status_code = 502


class GuardrailViolationError(LeadForgeError):
    """Raised if code attempts an action outside the passive-analysis boundary.

    This should never be triggered in normal operation — it exists as a
    defense-in-depth trip wire inside PassiveHttpClient (see
    services/security_audit).
    """

    code = "guardrail_violation"
    status_code = 400
