from pathlib import Path

import numpy as np
import trimesh
from fastapi.testclient import TestClient

from app.main import MODELS_DIR, app
from app.mesh_editing import ClarificationRequiredError, DeterministicMeshEditor, UnsupportedEditError, validate_for_print


editor = DeterministicMeshEditor()
source = trimesh.creation.box(extents=(20, 30, 40))
edited = editor.apply(source, "make it 50% wider, 80 mm tall, rotate 90 degrees around z, move 10 mm right")
assert edited.change_kind == "geometry"
assert np.allclose(edited.mesh.extents, (30, 30, 80), atol=0.01)
assert round(float(edited.mesh.bounding_box.centroid[0])) == 10
assert validate_for_print(edited.mesh)["watertight"]

with_base = editor.apply(source, "add a 5 mm base")
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
exact_height = editor.apply(source, "Make the object 150 mm tall.")
assert round(float(exact_height.mesh.extents[2])) == 150
wider = editor.apply(source, "Increase its width by 10 mm.")
assert np.allclose(wider.mesh.extents, (30, 30, 40))
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
    response = client.post(
        "/v1/geometry/edit",
        json={
            "label": "fixture",
            "model_url": "http://testserver/v1/geometry/models/editing-test-source.glb",
            "prompt": "make it 60 mm tall and move 5 mm right",
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
    assert round(float(exported.extents[2])) == 60
    assert round(float(exported.bounding_box.centroid[0])) == 5
    typed = client.post(
        "/v1/geometry/edit",
        json={
            "label": "fixture",
            "model_url": "http://testserver/v1/geometry/models/editing-test-source.glb",
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
            "model_url": "http://testserver/v1/geometry/models/editing-test-source.glb",
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
            "model_url": "http://testserver/v1/geometry/models/editing-test-source.glb",
            "prompt": "Change its color to red.",
        },
    )
    color_job = client.get(f"/v1/geometry/jobs/{color.json()['job_id']}").json()
    assert color_job["status"] == "done", color_job
    assert color_job["result"]["change_kind"] == "visual_only"
    assert (MODELS_DIR / color_job["result"]["model_name"]).is_file()
fixture.unlink(missing_ok=True)
print("mesh editing PASS")
