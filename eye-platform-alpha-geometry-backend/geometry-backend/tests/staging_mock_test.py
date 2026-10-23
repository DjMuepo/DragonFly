from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.environment import staging_mock_allowed, validate_mock_provider_settings
from app.providers import ReconstructionRequest, StagingMockProvider, select_provider

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
staging_blueprint = (REPOSITORY_ROOT / "deployment" / "render.staging.yaml").read_text(encoding="utf-8")
assert "name: dragonfly-staging-geometry-backend" in staging_blueprint
assert "name: dragonfly-staging-frontend" in staging_blueprint
assert "name: eye-geometry-backend" not in staging_blueprint and "name: dragonfly-frontend" not in staging_blueprint
assert "autoDeploy: false" in staging_blueprint
assert "REPLICATE_API_TOKEN" not in staging_blueprint
assert "EYE_STORAGE_DURABLE\n        value: \"0\"" in staging_blueprint
assert "EYE_REQUIRE_DURABLE_STORAGE\n        value: \"1\"" in staging_blueprint

with patch.dict(os.environ, {"EYE_APP_ENV": "production", "RENDER": "true", "RENDER_SERVICE_NAME": "dragonfly-production-backend", "EYE_ENABLE_MOCK_PROVIDER": "1", "EYE_RECONSTRUCTION_PROVIDER": "mock-test"}):
    assert not staging_mock_allowed()
    try:
        validate_mock_provider_settings()
    except RuntimeError:
        pass
    else:
        raise AssertionError("mock provider must fail closed on production Render")
    try:
        select_provider()
    except RuntimeError:
        pass
    else:
        raise AssertionError("production must not select the mock provider")

with patch.dict(os.environ, {"EYE_APP_ENV": "staging", "RENDER": "true", "RENDER_SERVICE_NAME": "dragonfly-staging-geometry-backend", "EYE_ENABLE_MOCK_PROVIDER": "1", "EYE_RECONSTRUCTION_PROVIDER": "mock-test"}):
    validate_mock_provider_settings()
    assert isinstance(select_provider(), StagingMockProvider)
    with tempfile.TemporaryDirectory(prefix="dragonfly-mock-provider-") as temp:
        output = select_provider().generate(ReconstructionRequest(label="staging test cup", confidence=0.5), Path(temp))
        assert output.provider_kind == "mock_test"
        assert output.notes.startswith("TEST DATA:")
        assert output.reconstruction_quality["fidelity_verified"] is False
        assert output.model_path.is_file()

print("staging mock provider PASS")
