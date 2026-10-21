import hashlib
import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from app.local_inference_contract import GLBArtifact, InferenceError, InferenceState, InferenceStatus, LocalInferenceRequest, ModelIdentity, ResourceSample


class LocalInferenceContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.image = self.root / "image.png"
        Image.new("RGB", (256, 128), "blue").save(self.image)
        self.image_hash = hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.model = ModelIdentity("test-contract-only", "immutable-test-revision", "a" * 64, "https://example.invalid/license", True)

    def tearDown(self):
        self.temporary.cleanup()

    def test_input_format_hash_and_dimensions(self):
        request = LocalInferenceRequest("test-only", self.image, self.image_hash, self.model)
        self.assertEqual(request.validate_input()["dimensions"], [256, 128])
        with self.assertRaisesRegex(ValueError, "checksum"):
            LocalInferenceRequest("test", self.image, "b" * 64, self.model).validate_input()
        with self.assertRaisesRegex(ValueError, "pixel"):
            LocalInferenceRequest("test", self.image, self.image_hash, self.model, max_image_pixels=10).validate_input()

    def test_weight_review_required(self):
        unreviewed = ModelIdentity("test", "version", "a" * 64, "https://example.invalid/license")
        with self.assertRaises(PermissionError):
            LocalInferenceRequest("test", self.image, self.image_hash, unreviewed).validate_input()

    def test_unknown_resources_and_invalid_measurements(self):
        self.assertIsNone(ResourceSample().gpu_used_mib)
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                ResourceSample(host_rss_mib=value)

    def test_failure_never_becomes_success(self):
        status = InferenceStatus("test", InferenceState.FAILED, 45, error=InferenceError("GPU_OOM", "Worker capacity exceeded."))
        self.assertIsNone(status.artifact)
        with self.assertRaises(ValueError):
            InferenceStatus("test", InferenceState.COMPLETE, 100)
        with self.assertRaises(ValueError):
            InferenceStatus("test", InferenceState.FAILED, 20)

    def test_container_validation_not_ai_execution_or_fidelity(self):
        artifact_path = self.root / "test-container.glb"
        artifact_path.write_bytes(struct.pack("<4sII", b"glTF", 2, 20) + b"12345678")
        checksum = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        artifact = GLBArtifact(artifact_path, checksum, self.model, self.image_hash, "fake-test-execution")
        artifact.validate_container()
        status = InferenceStatus("fake-status-test", InferenceState.COMPLETE, 100, artifact=artifact)
        self.assertEqual(status.state, InferenceState.COMPLETE)
        artifact_path.write_bytes(b"not a GLB")
        with self.assertRaises(ValueError):
            artifact.validate_container()

    def test_no_error_on_running_status(self):
        with self.assertRaises(ValueError):
            InferenceStatus("test", InferenceState.RUNNING, 10, error=InferenceError("TEST", "Not an inference."))


if __name__ == "__main__":
    unittest.main()