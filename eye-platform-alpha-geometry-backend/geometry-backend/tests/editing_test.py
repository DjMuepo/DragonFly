from pathlib import Path

import numpy as np
import trimesh
from fastapi.testclient import TestClient

from app.main import MODELS_DIR, app
from app.mesh_editing import ClarificationRequiredError, DeterministicMeshEditor, UnsupportedEditError, validate_for_print
from app.physical_units import metadata_path, parse_known_measurement


editor = DeterministicMeshEditor()
source = trimesh.creation.box(extents=(20, 30, 40))
edited = editor.apply(source, "make it 50% wider, 80 mm tall, rotate 90 degrees around z, move 10 mm right", scale_status="calibrated")
assert edited.change_kind == "geometry"
assert np.allclose(edited.mesh.extents, (30, 30, 80), atol=0.01)
assert round(float(edited.mesh.bounding_box.centroid[0])) == 10
assert validate_for_print(edited.mesh, "calibrated")["watertight"]

with_base = editor.apply(source, "add a 5 mm base", scale_status="calibrated")
assert len(list(with_base.mesh.split())) == 2
without_base = editor.apply(with_base.mesh, "remove base")
assert np.allclose(without_base.mesh.extents, source.extents)
assert editor.apply(source, "make it blue").change_kind == "visual_only"
try:
    editor.apply(source, "Make this bottle taller.")
except ClarificationRequiredError as error:
    assert "How much" in str(error)
else:
    raise AssertionError("ambiguous typed command did not request clarification")
height_percent = editor.apply(source, "Increase the height by 25%.")
assert np.allclose(height_percent.mesh.extents, (20, 30, 50))
assert editor.apply(source, "Change its color to red.").change_kind == "visual_only"
rotated = editor.apply(source, "Rotate the bottle 45 degrees.")
assert np.allclose(rotated.mesh.extents[:2], (35.355, 35.355), atol=0.01)
exact_height = editor.apply(source, "Make the object 150 mm tall.", scale_status="calibrated")
assert round(float(exact_height.mesh.extents[2])) == 150
wider = editor.apply(source, "Increase its width by 10 mm.", scale_status="calibrated")
assert np.allclose(wider.mesh.extents, (30, 30, 40))
try:
    editor.apply(source, "Make the object 150 mm tall.")
except ClarificationRequiredError as error:
    assert "Calibrate" in str(error)
else:
    raise AssertionError("unknown-scale mesh accepted an absolute mm edit")
assert parse_known_measurement("This bottle is 18 cm tall.") == (2, "height", 180.0)
assert np.isclose(parse_known_measurement("height is 7.086614 inches")[2], 180, atol=0.01)
assert parse_known_measurement("This object is 0.18 meters tall.") == (2, "height", 180.0)
try:
    editor.apply(source, "add a handle")
except UnsupportedEditError:
    pass
else:
    raise AssertionError("unsupported handle edit was accepted")

fixture = MODELS_DIR / "editing-test-source.glb"
source.export(fixture)
with TestClient(app) as client:
    capabilities = client.get("/v1/geometry/edit/capabilities").json()
    assert capabilities["features"] == ["base"]
    generated = client.post("/v1/geometry/generate", json={"label": "bottle"})
    generated_job = client.get(f"/v1/geometry/jobs/{generated.json()['job_id']}").json()
    assert generated_job["result"]["scale_status"] == "unknown"
    assert generated_job["result"]["validation"]["dimensions_mm"] is None
    assert any("Physical dimensions are unknown" in warning for warning in generated_job["result"]["validation"]["warnings"])
    uncalibrated = client.post(
        "/v1/geometry/edit",
        json={
            "label": "fixture",
            "model_url": "http://testserver/v1/geometry/models/editing-test-source.glb",
            "prompt": "make it 60 mm tall",
        },
    )
    uncalibrated_job = client.get(f"/v1/geometry/jobs/{uncalibrated.json()['job_id']}").json()
    assert uncalibrated_job["status"] == "error" and "Calibrate" in uncalibrated_job["error"]
    calibration = client.post(
        "/v1/geometry/calibrate",
        json={
            "label": "sample bottle",
            "model_url": "http://testserver/v1/geometry/models/editing-test-source.glb",
            "measurement": "This bottle is 180 mm tall.",
        },
    )
    calibration_job = client.get(f"/v1/geometry/jobs/{calibration.json()['job_id']}").json()
    assert calibration_job["status"] == "done", calibration_job
    calibrated = calibration_job["result"]
    assert calibrated["scale_status"] == "calibrated"
    assert calibrated["calibration"]["value_mm"] == 180
    assert calibrated["validation"]["dimensions_mm"]["height"] == 180
    calibrated_glb = trimesh.load(MODELS_DIR / calibrated["model_name"], force="mesh")
    calibrated_stl = trimesh.load((MODELS_DIR / calibrated["model_name"]).with_suffix(".stl"), force="mesh")
    assert np.isclose(calibrated_glb.extents[2], 0.18, atol=1e-5)
    assert np.isclose(calibrated_stl.extents[2], 180, atol=1e-3)
    response = client.post(
        "/v1/geometry/edit",
        json={
            "label": "fixture",
            "model_url": calibrated["model_url"],
            "prompt": "make it 200 mm tall and move 5 mm right",
        },
    )
    job = client.get(f"/v1/geometry/jobs/{response.json()['job_id']}").json()
    assert job["status"] == "done", job
    result = job["result"]
    assert result["change_kind"] == "geometry"
    assert result["validation"]["watertight"] is True
    assert result["model_url"].endswith(".glb")
    assert result["stl_download_url"].endswith(".stl")
    exported = trimesh.load(MODELS_DIR / result["model_name"], force="mesh")
    exported_stl = trimesh.load((MODELS_DIR / result["model_name"]).with_suffix(".stl"), force="mesh")
    assert np.isclose(exported.extents[2], 0.2, atol=1e-5)
    assert round(float(exported_stl.extents[2])) == 200
    assert round(float(exported_stl.bounding_box.centroid[0])) == 5
    assert result["scale_status"] == "calibrated"
    typed = client.post(
        "/v1/geometry/edit",
        json={
            "label": "fixture",
            "model_url": calibrated["model_url"],
            "prompt": "Increase the height by 25%.",
        },
    )
    typed_job = client.get(f"/v1/geometry/jobs/{typed.json()['job_id']}").json()
    assert typed_job["status"] == "done", typed_job
    assert typed_job["result"]["operations"] == ["increase height by 25%"]
    clarification = client.post(
        "/v1/geometry/edit",
        json={
            "label": "fixture",
            "model_url": calibrated["model_url"],
            "prompt": "Make this bottle taller.",
        },
    )
    clarification_job = client.get(f"/v1/geometry/jobs/{clarification.json()['job_id']}").json()
    assert clarification_job["status"] == "error"
    assert "How much" in clarification_job["error"]
    color = client.post(
        "/v1/geometry/edit",
        json={
            "label": "fixture",
            "model_url": calibrated["model_url"],
            "prompt": "Change its color to red.",
        },
    )
    color_job = client.get(f"/v1/geometry/jobs/{color.json()['job_id']}").json()
    assert color_job["status"] == "done", color_job
    assert color_job["result"]["change_kind"] == "visual_only"
    assert (MODELS_DIR / color_job["result"]["model_name"]).is_file()
fixture.unlink(missing_ok=True)
metadata_path(fixture).unlink(missing_ok=True)
print("mesh editing PASS")
