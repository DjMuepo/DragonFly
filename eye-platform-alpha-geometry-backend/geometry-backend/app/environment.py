from __future__ import annotations

import os

STAGING_SERVICE_NAME = "dragonfly-staging-geometry-backend"


def application_environment() -> str:
    configured = os.environ.get("EYE_APP_ENV", "").strip().lower()
    if configured:
        return configured
    if os.environ.get("RENDER") == "true" or os.environ.get("RENDER_SERVICE_ID"):
        return "production"
    return "development"


def staging_mock_allowed() -> bool:
    if application_environment() == "test":
        return not (os.environ.get("RENDER") == "true" or os.environ.get("RENDER_SERVICE_ID"))
    if application_environment() != "staging":
        return False
    if os.environ.get("RENDER") == "true" or os.environ.get("RENDER_SERVICE_ID"):
        return os.environ.get("RENDER_SERVICE_NAME") == STAGING_SERVICE_NAME
    return True


def validate_mock_provider_settings() -> None:
    enabled = os.environ.get("EYE_ENABLE_MOCK_PROVIDER") == "1"
    requested = os.environ.get("EYE_RECONSTRUCTION_PROVIDER", "dpt-depth-mesh").strip().lower()
    if enabled and not staging_mock_allowed():
        raise RuntimeError("EYE_ENABLE_MOCK_PROVIDER is restricted to test or the explicitly named DragonFly staging service.")
    if requested in {"mock-test", "mock"} and not enabled:
        raise RuntimeError("The mock-test provider requires EYE_ENABLE_MOCK_PROVIDER=1 in an allowed test/staging environment.")
    if requested in {"mock-test", "mock"} and not staging_mock_allowed():
        raise RuntimeError("The mock-test provider is unavailable outside test or the explicitly named DragonFly staging service.")
