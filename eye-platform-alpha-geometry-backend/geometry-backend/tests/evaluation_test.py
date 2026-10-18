import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import trimesh
from PIL import Image, ImageDraw

from evaluation.cli import main, prepare_case
from evaluation.cohort import cohort_plan, import_camera_photo, initialize_cohort, validate_cohort
from evaluation.dataset import add_case, initialize_fixtures, load_dataset
from evaluation.isolation import GrabCutSegmentation, digest, prepare_baseline
from evaluation.metrics import inspect_model, mask_metrics
from evaluation.predictions import authorize, cache_key, prediction_plan, run_prediction, write_json
from app.providers import ReplicateGPUProvider


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.jpg"
        with Image.new("RGB", (320, 240), "white") as image:
            ImageDraw.Draw(image).rectangle((60, 40, 240, 200), fill="blue")
            exif = Image.Exif()
            exif[274] = 6
            image.save(self.source, exif=exif)
        self.environment = patch.dict(os.environ, {"EYE_LOCAL_SEGMENTATION": "0", "DRAGONFLY_EVAL_GRABCUT": "0", "DRAGONFLY_EVAL_PAID": "0"})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def make_dataset(self):
        return add_case(self.root / "dataset", self.source, "real-test", "opaque", "test image", "synthetic", "controlled", "plain", [], "Known drawn rectangle, not a photograph.")

    def test_fixtures_inventory_and_immutability(self):
        cases = initialize_fixtures(self.root / "dataset")
        self.assertEqual(len(cases), 11)
        self.assertEqual(len({case["category"] for case in cases}), 5)
        self.assertTrue(all(case["kind"] == "synthetic" and case["expected_mask"] for case in cases))
        original = self.root / "dataset" / cases[0]["image"]
        original.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            load_dataset(self.root / "dataset")

    def test_six_object_cohort_pending_and_cost_plan(self):
        root = self.root / "cohort"
        initialize_cohort(root)
        plan = cohort_plan(root)
        self.assertEqual(plan["ready_photos"], 0)
        self.assertEqual(len(plan["missing_photos"]), 6)
        self.assertEqual(plan["maximum_new_predictions"], 12)
        self.assertIsNone(plan["estimated_cost_for_12_usd"])
        self.assertEqual(len(list((root / "inputs").iterdir())), 6)
        priced = cohort_plan(root, "test-only-version", 0.2)
        self.assertAlmostEqual(priced["estimated_cost_for_12_usd"], 2.4)
        self.assertEqual(priced["paid_predictions_executed"], 0)

    def test_real_cohort_requires_camera_confirmation_and_metadata(self):
        root = self.root / "cohort"
        initialize_cohort(root)
        arguments = (root, "opaque-bottle", self.source, "unit-test light", "unit-test background", "none", "opaque", "2026-10-18")
        with self.assertRaises(PermissionError):
            import_camera_photo(*arguments, False)
        original_hash = digest(self.source)
        item = import_camera_photo(*arguments, True)
        self.assertEqual(item["status"], "ready")
        self.assertEqual(item["sha256"], original_hash)
        self.assertEqual(digest(self.source), original_hash)
        self.assertEqual(item["pixel_dimensions"], [320, 240])
        self.assertEqual(item["exif_orientation"], 6)
        self.assertEqual(cohort_plan(root)["ready_photos"], 1)
        with self.assertRaisesRegex(ValueError, "overwriting"):
            import_camera_photo(*arguments, True)
        cohort = validate_cohort(root)
        cohort["objects"][0]["lighting"] = "mismatched"
        write_json(root / "cohort.json", cohort)
        with self.assertRaisesRegex(ValueError, "lighting"):
            validate_cohort(root)

    def test_real_cohort_rejects_synthetic_or_screenshot_substitute(self):
        root = self.root / "cohort"
        initialize_cohort(root)
        import_camera_photo(root, "opaque-bottle", self.source, "unit-test", "unit-test", "none", "opaque", "2026-10-18", True)
        manifest = root / "dataset/manifest.json"
        data = json.loads(manifest.read_text())
        for kind in ("synthetic", "screenshot_proxy"):
            data["cases"][0]["kind"] = kind
            write_json(manifest, data)
            with self.assertRaisesRegex(ValueError, "original camera photograph"):
                validate_cohort(root)

    def test_pending_real_cohort_cli_never_prepares_or_spends(self):
        root = self.root / "cohort"
        with patch.object(ReplicateGPUProvider, "_request", side_effect=AssertionError("Network forbidden")) as transport, redirect_stdout(io.StringIO()):
            main(["init-real", "--cohort", str(root)])
            main(["validate-real", "--cohort", str(root)])
            main(["plan-real", "--cohort", str(root)])
            with self.assertRaises(SystemExit) as stopped:
                main(["prepare-real", "--cohort", str(root), "--output", str(self.root / "output")])
            self.assertEqual(stopped.exception.code, 2)
            self.assertFalse(transport.called)
        self.assertTrue((root / "preparation.html").is_file())
        self.assertFalse((self.root / "output").exists())

    def test_paired_inputs_share_original_and_fallback(self):
        self.make_dataset()
        with patch.dict(os.environ, {"DRAGONFLY_EVAL_GRABCUT": "1"}):
            import cv2

            with patch.object(cv2, "grabCut", side_effect=cv2.error("uncertain")):
                record = prepare_case(self.root / "dataset", self.root / "output", "real-test", "grabcut", "STANDARD")
        self.assertEqual(digest(Path(record["original"])), record["case"]["sha256"])
        self.assertEqual(record["pipelines"]["A"]["metadata"]["image_sha256"], record["pipelines"]["B"]["metadata"]["image_sha256"])
        plan = prediction_plan([record], self.root / "output", "test-only-version", None)
        self.assertEqual(plan["new_predictions"], 1)
        self.assertEqual(plan["entries"][0]["cases"], ["real-test:A", "real-test:B"])

    def test_photo_metadata_and_no_overwrite(self):
        original_hash = digest(self.source)
        case = self.make_dataset()
        self.assertEqual(case["exif_orientation"], 6)
        self.assertEqual(case["sha256"], original_hash)
        self.assertEqual(digest(self.source), original_hash)
        self.assertIsNone(case["known_dimensions_mm"])
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.make_dataset()

    def test_identifier_traversal_rejected(self):
        with self.assertRaises(ValueError):
            add_case(self.root / "dataset", self.source, "../bad", "opaque", "box", "photo", "unknown", "unknown", [], "unknown")

    def test_wrong_annotation_dimensions_rejected(self):
        truth = self.root / "wrong-size.png"
        Image.new("L", (20, 20), 255).save(truth)
        with self.assertRaisesRegex(ValueError, "oriented"):
            add_case(self.root / "dataset", self.source, "wrong-mask", "opaque", "box", "synthetic", "controlled", "plain", [], "rectangle", mask=truth)

    def test_iphone_sized_worker_memory_and_orientation(self):
        source = self.root / "iphone-sized.jpg"
        with Image.new("RGB", (4032, 3024), "white") as image:
            ImageDraw.Draw(image).rectangle((1000, 600, 3000, 2500), fill="blue")
            exif = Image.Exif()
            exif[274] = 6
            image.save(source, exif=exif)
        dataset = self.root / "dataset"
        add_case(dataset, source, "synthetic-iphone", "geometric", "12 MP drawn fixture", "synthetic", "synthetic", "plain", [], "Synthetic rectangle, not an iPhone photograph.")
        output = self.root / "output"
        with patch.dict(os.environ, {"DRAGONFLY_EVAL_GRABCUT": "1"}):
            subprocess.run([sys.executable, "-m", "evaluation.cli", "_case", "--dataset", str(dataset), "--output", str(output), "--case", "synthetic-iphone", "--isolation", "grabcut"], check=True)
        record = json.loads((output / "synthetic-iphone/case.json").read_text())
        self.assertLess(record["peak_rss_mib"], 512)
        self.assertEqual(record["pipelines"]["A"]["metadata"]["exif_orientation"], 6)
        self.assertEqual(record["pipelines"]["A"]["metadata"]["output_dimensions"], [960, 1280])

    def test_flag_and_exact_fallback(self):
        baseline = prepare_baseline(self.source, self.root / "a")
        with Image.open(baseline.path) as image:
            self.assertGreater(image.height, image.width)
        with self.assertRaises(PermissionError):
            GrabCutSegmentation().prepare(baseline, self.root / "b")
        with patch.dict(os.environ, {"DRAGONFLY_EVAL_GRABCUT": "1"}):
            import cv2

            with patch.object(cv2, "grabCut", side_effect=cv2.error("ambiguous")):
                result = GrabCutSegmentation().prepare(baseline, self.root / "b")
        self.assertTrue(result.metadata["fallback"])
        self.assertEqual(result.path.read_bytes(), baseline.path.read_bytes())
        self.assertEqual(result.metadata["components_discarded"], 0)
        self.assertTrue(result.mask.is_file())

    def test_metrics_known_mask(self):
        truth = self.root / "truth.png"
        mask = Image.new("L", (10, 10), 0)
        ImageDraw.Draw(mask).rectangle((0, 0, 4, 9), fill=255)
        mask.save(truth)
        score = mask_metrics(truth, truth, truth, (10, 10))
        self.assertEqual(score["silhouette_iou"], 1)
        self.assertEqual(score["background_contamination"], 0)
        self.assertEqual(score["important_detail_recall"], 1)
        unmasked = mask_metrics(None, truth, None, (10, 10))
        self.assertEqual(unmasked["foreground_completeness"], 1)
        self.assertEqual(unmasked["background_contamination"], 0.5)
        self.assertFalse(mask_metrics(None, None, None, (10, 10))["measured"])

    def test_model_validity_is_not_fidelity(self):
        model = self.root / "saved.glb"
        trimesh.creation.box().export(model)
        result = inspect_model(model)
        self.assertTrue(result["geometric_validity"]["watertight"])
        self.assertFalse(result["fidelity_verified"])
        self.assertIsNone(result["visual_similarity"])
        self.assertIsNone(result["bounding_box_mm"])

    def test_plan_deduplicates_and_cost_guard(self):
        records = [{"case": {"id": "test"}, "pipelines": {"A": {"input": str(self.source)}, "B": {"input": str(self.source)}}}]
        plan = prediction_plan(records, self.root, "owner/model:version", 0.2)
        self.assertEqual(plan["new_predictions"], 1)
        self.assertEqual(plan["estimated_cost_usd"], 0.2)
        with self.assertRaises(PermissionError):
            authorize(plan, True, 2, 1, False)
        with patch.dict(os.environ, {"DRAGONFLY_EVAL_PAID": "1"}):
            with self.assertRaises(PermissionError):
                authorize(plan, True, 0, 1, False)
            with self.assertRaises(PermissionError):
                authorize(plan, True, 2, 0.1, False)
            authorize(plan, True, 1, 0.2, False)
            unknown = prediction_plan(records, self.root, "owner/model:version", None)
            with self.assertRaises(PermissionError):
                authorize(unknown, True, 2, None, False)

    def test_cli_dry_run_never_requests_provider(self):
        self.make_dataset()
        with patch.object(ReplicateGPUProvider, "_request", side_effect=AssertionError("Network forbidden")) as transport, redirect_stdout(io.StringIO()) as output:
            main(["pair", "--dataset", str(self.root / "dataset"), "--output", str(self.root / "output"), "--model-version", "owner/model:version"])
        self.assertFalse(transport.called)
        self.assertIn('"new_predictions": 1', output.getvalue())
        self.assertTrue((self.root / "output/comparison.html").is_file())
        records = json.loads((self.root / "output/results.json").read_text())
        self.assertIsNone(records[0]["pipelines"]["A"]["prediction"])

    def test_paid_non_photo_requires_separate_acknowledgement(self):
        self.make_dataset()
        with patch.dict(os.environ, {"DRAGONFLY_EVAL_PAID": "1"}), patch.object(ReplicateGPUProvider, "_request", side_effect=AssertionError("Network forbidden")) as transport, redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                main(["pair", "--dataset", str(self.root / "dataset"), "--output", str(self.root / "output"), "--model-version", "version", "--execute", "--authorize-predictions", "2", "--accept-unknown-cost"])
            self.assertEqual(stopped.exception.code, 2)
            self.assertFalse(transport.called)

    def test_uncertain_submission_never_retries(self):
        directory = self.root / "cache" / cache_key(self.source, "version")
        write_json(directory / "record.json", {"state": "submitting"})
        with patch.object(ReplicateGPUProvider, "_request", side_effect=AssertionError("Network forbidden")) as transport:
            with self.assertRaises(RuntimeError):
                run_prediction(self.source, self.root, "version")
            self.assertFalse(transport.called)

    def test_pending_prediction_resume_and_completed_cache(self):
        glb = trimesh.creation.box().export(file_type="glb")
        pending = {"id": "fake-local-test", "status": "starting", "urls": {"get": "https://example.invalid/prediction"}}
        succeeded = {"id": "fake-local-test", "status": "succeeded", "output": {"mesh": "https://example.invalid/model.glb"}}
        with patch.dict(os.environ, {"DRAGONFLY_EVAL_PAID": "1", "REPLICATE_API_TOKEN": "fake-test-token"}), patch.object(ReplicateGPUProvider, "_request", side_effect=[pending, succeeded]) as transport, patch("urllib.request.urlopen", return_value=io.BytesIO(glb)):
            with self.assertRaises(TimeoutError):
                run_prediction(self.source, self.root, "version", timeout_seconds=0)
            result = run_prediction(self.source, self.root, "version")
            cached = run_prediction(self.source, self.root, "version")
        self.assertEqual(transport.call_args_list[0].args[0], "POST")
        self.assertEqual(transport.call_args_list[1].args[0], "GET")
        self.assertEqual(transport.call_count, 2)
        self.assertTrue(cached["reused_cache"])
        self.assertEqual(result["prediction_id"], "fake-local-test")
        self.assertFalse(result["fidelity_verified"])

    def test_failed_or_corrupt_cache_never_recharges(self):
        directory = self.root / "cache" / cache_key(self.source, "version")
        write_json(directory / "record.json", {"state": "failed"})
        with self.assertRaises(RuntimeError):
            run_prediction(self.source, self.root, "version")
        write_json(directory / "record.json", {"state": "complete", "model_file": "missing.glb", "model_sha256": "wrong"})
        with self.assertRaises(ValueError):
            run_prediction(self.source, self.root, "version")

    def test_human_review_required_and_saved_outputs_import(self):
        self.make_dataset()
        output = self.root / "output"
        with redirect_stdout(io.StringIO()):
            main(["prepare", "--dataset", str(self.root / "dataset"), "--output", str(output)])
        record = json.loads((output / "results.json").read_text())[0]
        self.assertEqual(record["human_review"]["outcome"], "pending")
        self.assertFalse(record["promotion"]["eligible"])
        model = self.root / "saved.glb"
        trimesh.creation.box().export(model)
        main(["attach-model", "--output", str(output), "--case", "real-test", "--arm", "A", "--glb", str(model), "--input-sha256", digest(Path(record["pipelines"]["A"]["input"])), "--model-version", "unknown-historical-version"])
        main(["review", "--output", str(output), "--case", "real-test", "--reviewer", "local-test", "--outcome", "inconclusive", "--notes", "Synthetic unit test only; not a fidelity validation.", "--a-fidelity", "unknown", "--b-fidelity", "unknown"])
        updated = json.loads((output / "results.json").read_text())[0]
        self.assertIn("not newly inferred", updated["pipelines"]["A"]["prediction"]["evidence"])
        self.assertEqual(updated["human_review"]["outcome"], "inconclusive")
        prepare_case(self.root / "dataset", output, "real-test", "baseline", "STANDARD")
        preserved = json.loads((output / "real-test/case.json").read_text())
        self.assertEqual(preserved["human_review"]["outcome"], "inconclusive")
        preserved["pipelines"]["A"]["metadata"]["image_sha256"] = "outdated"
        write_json(output / "real-test/case.json", preserved)
        prepare_case(self.root / "dataset", output, "real-test", "baseline", "STANDARD")
        invalidated = json.loads((output / "real-test/case.json").read_text())
        self.assertEqual(invalidated["human_review"]["outcome"], "pending")


if __name__ == "__main__":
    unittest.main()