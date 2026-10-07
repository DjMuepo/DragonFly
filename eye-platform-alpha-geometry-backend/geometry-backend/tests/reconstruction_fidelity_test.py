import base64
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from app.image_preprocessing import prepare_reconstruction_image
from app.providers import ReconstructionRequest, ReplicateGPUProvider
from app.reconstruction_debug import assess_reconstruction, save_debug_record
from app.main import app, MODELS_DIR


os.environ["EYE_LOCAL_SEGMENTATION"] = "0"

with TemporaryDirectory() as temporary:
    root = Path(temporary)
    transposes = {
        1: None,
        2: Image.Transpose.FLIP_LEFT_RIGHT,
        3: Image.Transpose.ROTATE_180,
        4: Image.Transpose.FLIP_TOP_BOTTOM,
        5: Image.Transpose.TRANSPOSE,
        6: Image.Transpose.ROTATE_270,
        7: Image.Transpose.TRANSVERSE,
        8: Image.Transpose.ROTATE_90,
    }
    source = Image.new("RGB", (320, 240), "white")
    draw = ImageDraw.Draw(source)
    draw.rectangle((0, 0, 159, 119), fill="red")
    draw.rectangle((160, 0, 319, 119), fill="blue")
    draw.rectangle((0, 120, 159, 239), fill="green")
    for orientation, transpose in transposes.items():
        path = root / f"orientation-{orientation}.png"
        exif = Image.Exif()
        exif[274] = orientation
        source.save(path, exif=exif)
        original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        prepared, report = prepare_reconstruction_image(path, root)
        expected = source.transpose(transpose) if transpose is not None else source.copy()
        with Image.open(prepared) as image:
            assert image.size == expected.size
            for point in [(30, 30), (image.width - 30, 30), (30, image.height - 30), (image.width - 30, image.height - 30)]:
                assert np.allclose(image.getpixel(point), expected.getpixel(point), atol=8)
        assert original_hash == hashlib.sha256(path.read_bytes()).hexdigest()
        assert report.exif_orientation == orientation
        payload = ReplicateGPUProvider._encode_image(prepared)
        exact = base64.b64decode(payload.split(",", 1)[1])
        assert exact == prepared.read_bytes()
        assert hashlib.sha256(exact).hexdigest() == report.image_sha256
        manifest = save_debug_record(root / "debug", f"orientation-{orientation}", {"preprocessing": report.as_dict()}, exact)
        record = json.loads(manifest.read_text())
        assert Path(record["submitted_image_path"]).read_bytes() == exact
        assert record["submitted_image_sha256"] == report.image_sha256
        assert manifest.stat().st_mode & 0o077 == 0
        expected.close()
    source.close()
    for index in range(25):
        save_debug_record(root / "debug", f"retention-{index}", {"stage": "input"}, b"image")
    assert len(list((root / "debug").glob("*.json"))) <= 20
    assert len(list((root / "debug").glob("*.input.*"))) <= 20

normal = trimesh.creation.box(extents=(20, 30, 40))
normal_report = assess_reconstruction(normal)
assert normal_report["status"] == "not_flagged"
assert normal_report["fidelity_verified"] is False
duplicate = normal.copy()
duplicate.apply_translation((100, 0, 0))
duplicate_report = assess_reconstruction(trimesh.util.concatenate([normal, duplicate]))
assert duplicate_report["status"] == "warning"
assert duplicate_report["connected_surface_count"] == 2
assert duplicate_report["similar_component_pairs"] == [[0, 1]]
extreme_report = assess_reconstruction(trimesh.creation.box(extents=(1, 1, 100)))
assert extreme_report["status"] == "warning"
assert extreme_report["aspect_ratio"] == 100
_, body, _ = ReplicateGPUProvider._prediction_request("owner/model:test-version", "data:image/jpeg;base64,test")
assert body == {"version": "test-version", "input": {"image": "data:image/jpeg;base64,test"}}

with TemporaryDirectory() as temporary:
    root = Path(temporary)
    asset = root / "remote-test.glb"
    normal.export(asset)
    image_path = root / "test-source.png"
    image = Image.new("RGB", (320, 240), "white")
    ImageDraw.Draw(image).rectangle((80, 30, 240, 210), fill="blue")
    image.save(image_path)
    image.close()
    prediction = {"id": "test-prediction", "status": "succeeded", "urls": {"get": "https://example.invalid/prediction"}, "output": {"mesh": asset.as_uri()}}
    with patch.dict(os.environ, {"EYE_RECONSTRUCTION_PROVIDER": "replicate", "REPLICATE_API_TOKEN": "test-only", "EYE_REPLICATE_MODEL_VERSION": "owner/model:test-version", "EYE_RECONSTRUCTION_DEBUG": "1"}), patch.object(ReplicateGPUProvider, "_request", return_value=prediction) as transport:
        with TestClient(app) as client:
            response = client.post("/v1/geometry/generate-from-image", files={"image": ("test.png", image_path.read_bytes(), "image/png")})
            assert response.status_code == 202
            job_id = response.json()["job_id"]
            job = client.get(f"/v1/geometry/jobs/{job_id}").json()
            assert job["status"] == "done", job
            quality = job["result"]["reconstruction_quality"]
            assert quality["fidelity_verified"] is False
            assert quality["connected_surface_count"] == 1
            assert transport.call_count == 1
            sent = transport.call_args.args[3]["input"]["image"]
            exact = base64.b64decode(sent.split(",", 1)[1])
            debug_root = Path(__file__).resolve().parents[1] / "reconstruction_debug"
            manifest = debug_root / f"{job_id}.json"
            record = json.loads(manifest.read_text())
            captured = Path(record["submitted_image_path"])
            assert captured.read_bytes() == exact
            assert record["submitted_image_sha256"] == hashlib.sha256(exact).hexdigest()
            assert record["prediction_id"] == "test-prediction"
            assert record["prediction_status"] == "succeeded"
            assert record["model_reference"] == "owner/model:test-version"
            assert record["returned_asset_url"] == asset.as_uri()
            assert record["preprocessing"]["exif_orientation"] == 1
            captured.unlink()
            manifest.unlink()
            model = MODELS_DIR / job["result"]["model_name"]
            for path in (model, model.with_suffix(".stl"), model.with_suffix(".metadata.json")):
                path.unlink(missing_ok=True)
print("reconstruction fidelity diagnostics PASS (local invariants only; no inference)")