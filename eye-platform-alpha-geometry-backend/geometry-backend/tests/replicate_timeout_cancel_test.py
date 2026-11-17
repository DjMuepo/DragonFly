from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app.providers import ReconstructionRequest, ReplicateGPUProvider

CANCEL_URL = "https://api.replicate.com/v1/predictions/timeout-test/cancel"

transport_calls: list[tuple[str, str, bool]] = []


def fake_request(method: str, path: str, token: str, body, absolute: bool = False):
    transport_calls.append((method, path, absolute))
    if method == "POST" and path == "/predictions":
        return {
            "id": "timeout-test",
            "status": "processing",
            "urls": {
                "get": "https://api.replicate.com/v1/predictions/timeout-test",
                "cancel": CANCEL_URL,
            },
        }
    if method == "POST" and path == CANCEL_URL:
        return {"id": "timeout-test", "status": "canceled"}
    raise AssertionError(f"unexpected transport call: {method} {path}")


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    image_path = root / "bottle.jpg"
    Image.new("RGB", (32, 32), "white").save(image_path)
    request = ReconstructionRequest(label="bottle", confidence=0.9, image_path=image_path)
    environment = {
        "REPLICATE_API_TOKEN": "test-only",
        "EYE_REPLICATE_MODEL_VERSION": "owner/model:test-version",
        "EYE_REPLICATE_TIMEOUT_SECONDS": "0",
        "EYE_RECONSTRUCTION_DEBUG": "0",
    }
    with patch.dict(os.environ, environment), patch.object(
        ReplicateGPUProvider, "_request", staticmethod(fake_request)
    ):
        try:
            ReplicateGPUProvider().generate(request, root)
        except RuntimeError as error:
            message = str(error)
        else:
            raise AssertionError("expired polling deadline must raise")

assert "timed out after 0 seconds" in message, message
assert "cancellation requested" in message, message
assert transport_calls.count(("POST", "/predictions", False)) == 1, transport_calls
assert ("POST", CANCEL_URL, True) in transport_calls, transport_calls

# Cancellation failures must not mask the timeout error, only annotate it.
def failing_request(method: str, path: str, token: str, body, absolute: bool = False):
    if method == "POST" and path == "/predictions":
        return fake_request(method, path, token, body, absolute)
    raise RuntimeError("Replicate API error 500: cancel rejected")


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    image_path = root / "bottle.jpg"
    Image.new("RGB", (32, 32), "white").save(image_path)
    request = ReconstructionRequest(label="bottle", confidence=0.9, image_path=image_path)
    with patch.dict(os.environ, environment), patch.object(
        ReplicateGPUProvider, "_request", staticmethod(failing_request)
    ):
        try:
            ReplicateGPUProvider().generate(request, root)
        except RuntimeError as error:
            message = str(error)
        else:
            raise AssertionError("expired polling deadline must raise")

assert "timed out after 0 seconds" in message, message
assert "cancellation failed" in message, message

# A prediction payload without a cancel URL degrades gracefully.
assert ReplicateGPUProvider._cancel_prediction({"urls": {}}, "test-only").startswith("unavailable")
assert ReplicateGPUProvider._cancel_prediction({}, "test-only").startswith("unavailable")

print("replicate timeout cancel PASS")
