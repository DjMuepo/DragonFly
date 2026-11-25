"""Controlled-test safeguard for paid remote predictions.

A staging-only, persisted, global allowance for paid predictions. The allowance
is reserved atomically in the database immediately before a remote prediction
is submitted and is NEVER restored automatically afterwards, even when the
network outcome is ambiguous: an operator must inspect the Replicate dashboard
and, if appropriate, raise EYE_PAID_TEST_GLOBAL_LIMIT or edit the ledger.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Optional

from .accounts import EMAIL_PATTERN
from .environment import application_environment, controlled_paid_test_allowed
from .persistence.repository import Repository, Row

PAID_TEST_MODE_ENV = "EYE_PAID_TEST_MODE"
AUTHORIZED_EMAIL_ENV = "EYE_PAID_TEST_AUTHORIZED_USER_EMAIL"
GLOBAL_LIMIT_ENV = "EYE_PAID_TEST_GLOBAL_LIMIT"
MAX_GLOBAL_LIMIT = 10
PAID_PROVIDER_REQUESTS = {"replicate", "remote-gpu", "hunyuan3d", "trellis"}


class PaidTestGateError(Exception):
    """A request violated the controlled paid-test policy."""

    def __init__(self, message: str, status_code: int = 403, code: str = "paid_test_forbidden"):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def paid_test_mode_enabled() -> bool:
    return os.environ.get(PAID_TEST_MODE_ENV) == "1"


def configured_authorized_email() -> str:
    return os.environ.get(AUTHORIZED_EMAIL_ENV, "").strip().lower()


def configured_global_limit() -> int:
    raw = os.environ.get(GLOBAL_LIMIT_ENV, "1").strip()
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{GLOBAL_LIMIT_ENV} must be an integer, got {raw!r}.") from None


def validate_paid_test_settings() -> None:
    """Fail closed at startup on any unsafe paid-test configuration."""
    if paid_test_mode_enabled():
        if not controlled_paid_test_allowed():
            raise RuntimeError(
                f"{PAID_TEST_MODE_ENV}=1 is restricted to local tests or the explicitly named DragonFly staging service. "
                "It must never be enabled on production."
            )
        if not EMAIL_PATTERN.match(configured_authorized_email()):
            raise RuntimeError(
                f"{PAID_TEST_MODE_ENV}=1 requires {AUTHORIZED_EMAIL_ENV} to name the single authorized existing user account."
            )
        limit = configured_global_limit()
        if not 0 <= limit <= MAX_GLOBAL_LIMIT:
            raise RuntimeError(f"{GLOBAL_LIMIT_ENV} must be between 0 and {MAX_GLOBAL_LIMIT} for a controlled test.")
    requested = os.environ.get("EYE_RECONSTRUCTION_PROVIDER", "dpt-depth-mesh").strip().lower()
    if requested in PAID_PROVIDER_REQUESTS and application_environment() == "staging" and not paid_test_mode_enabled():
        raise RuntimeError(
            "The paid Replicate provider on staging requires the controlled test gate: set "
            f"{PAID_TEST_MODE_ENV}=1, {AUTHORIZED_EMAIL_ENV}, and {GLOBAL_LIMIT_ENV} (or switch back to mock-test)."
        )


class PaidPredictionGate:
    """Database-backed global allowance for paid predictions during the controlled test."""

    def __init__(self, repo: Repository):
        self.repo = repo

    @staticmethod
    def enabled() -> bool:
        return paid_test_mode_enabled()

    def consumed(self) -> int:
        return self.repo.count_paid_predictions()

    def authorize_request(self, user: Optional[Row]) -> None:
        """Reject paid reconstruction requests from guests and unauthorized accounts.

        No-op when the controlled test gate is disabled (non-staging deployments are unchanged;
        startup validation forbids the paid provider on staging without the gate).
        """
        if not paid_test_mode_enabled():
            return
        if user is None:
            raise PaidTestGateError(
                "Guest paid reconstruction is disabled during the controlled real-AI test. Sign in with the authorized account.",
                status_code=403,
                code="paid_test_guest_forbidden",
            )
        if (user.get("email") or "").strip().lower() != configured_authorized_email():
            raise PaidTestGateError(
                "This account is not authorized for the controlled real-AI test.",
                status_code=403,
                code="paid_test_unauthorized_user",
            )
        if self.consumed() >= configured_global_limit():
            raise PaidTestGateError(
                "The controlled-test paid prediction allowance is exhausted. No further paid predictions are permitted.",
                status_code=429,
                code="paid_test_allowance_exhausted",
            )

    def reserve(self, job_id: Optional[str]) -> str:
        """Atomically consume one unit of the global allowance; raises QuotaExceeded when exhausted.

        The reservation is persisted before the remote prediction is submitted and is never
        released automatically, so an ambiguous network failure cannot free budget for a retry.
        """
        if job_id is None:
            raise PaidTestGateError("Paid predictions outside a tracked reconstruction job are not allowed during the controlled test.")
        job = self.repo.get_job(job_id)
        owner = self.repo.get_user(job["owner_id"]) if job and job.get("owner_id") else None
        if owner is None or (owner.get("email") or "").strip().lower() != configured_authorized_email():
            raise PaidTestGateError("The controlled-test paid prediction must belong to the authorized user account.")
        reservation_id = uuid.uuid4().hex
        self.repo.reserve_paid_prediction(reservation_id, owner["id"], job_id, configured_global_limit(), time.time())
        return reservation_id

    def record_submission(self, reservation_id: str, prediction_id: str, model_reference: str) -> None:
        self.repo.record_paid_submission(reservation_id, prediction_id, model_reference, time.time())

    def status(self) -> dict:
        info: dict = {"enabled": paid_test_mode_enabled(), "environment_allowed": controlled_paid_test_allowed()}
        if info["enabled"]:
            limit = configured_global_limit()
            used = self.consumed()
            info.update(
                global_limit=limit,
                consumed=used,
                remaining=max(limit - used, 0),
                authorized_user_configured=bool(configured_authorized_email()),
            )
        return info


_ACTIVE_GATE: Optional[PaidPredictionGate] = None


def register_gate(gate: Optional[PaidPredictionGate]) -> None:
    global _ACTIVE_GATE
    _ACTIVE_GATE = gate


def reserve_before_submission(job_id: Optional[str]) -> Optional[str]:
    """Called by the Replicate provider immediately before the prediction POST."""
    if not paid_test_mode_enabled():
        return None
    if _ACTIVE_GATE is None:
        raise RuntimeError(
            f"{PAID_TEST_MODE_ENV}=1 but the paid prediction gate is not initialized; refusing to submit a paid prediction."
        )
    return _ACTIVE_GATE.reserve(job_id)


def record_submission(reservation_id: Optional[str], prediction_id: str, model_reference: str) -> None:
    if reservation_id and _ACTIVE_GATE is not None:
        _ACTIVE_GATE.record_submission(reservation_id, prediction_id, model_reference)
