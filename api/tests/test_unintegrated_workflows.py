import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import behavior_engine, printers, subscription_gate


class UnintegratedWorkflowTests(unittest.TestCase):
    def test_printer_submission_never_claims_success(self):
        result = printers.submit_print_job("prt_demo_1", {"family": "hook", "material": "PLA"})
        self.assertFalse(result["ok"])
        self.assertFalse(result["submitted"])
        self.assertEqual(result["status"], "not_integrated")

    def test_print_success_does_not_write_a_fabricated_event(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_path = Path(temporary) / "behavior.json"
            with patch.object(behavior_engine, "DATA_PATH", str(data_path)):
                result = behavior_engine.record_print_success({"title": "not verified", "printer_id": "prt_demo_1"})
            self.assertFalse(result["ok"])
            self.assertFalse(result["event_recorded"])
            self.assertFalse(data_path.exists())

    def test_client_cannot_claim_paid_subscription(self):
        self.assertFalse(subscription_gate.require_subscription({"is_paid": True})["allowed"])
        self.assertEqual(subscription_gate.require_subscription({"is_paid": True})["error"], "billing_not_integrated")


if __name__ == "__main__":
    unittest.main()