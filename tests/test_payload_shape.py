import json
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from f1watch.api.lambda_handler import _build_next_payload, lambda_handler  # noqa: E402


class TestDataShape(unittest.TestCase):
    def test_generated_schedule_timestamps_parse(self):
        schedule_path = REPO_ROOT / "2026_schedule.json"
        data = json.loads(schedule_path.read_text(encoding="utf-8"))
        self.assertGreater(len(data), 0)

        for item in data:
            self.assertIn("event", item)
            self.assertIn("session", item)
            self.assertIn("start", item)
            datetime.strptime(item["start"], "%Y-%m-%dT%H:%M:%S%z")

    def test_payload_shape_from_synthetic_inputs(self):
        sessions = [
            {"event": "Test", "session": "FP1", "start": "2099-01-01T10:00:00-00:00"},
            {"event": "Test", "session": "Q", "start": "2099-01-02T10:00:00-00:00"},
        ]
        teams = [{"team_name": "McLaren", "place": "1"}]
        drivers = [
            {"first_name": "Lando", "last_name": "Norris", "car_number": "4", "place": "1"}
        ]

        payload = _build_next_payload(sessions, teams, drivers, tz_offset_hours=-7)

        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["event"], "Test")
        self.assertEqual(payload["session"], "FP1")
        self.assertIn("dow", payload)
        self.assertIn("dom", payload)
        self.assertIn("delta", payload)
        self.assertEqual(payload["mclaren"], "1")
        self.assertEqual(payload["ln4"], "1")

    def test_lambda_handler_returns_json_body(self):
        old_env = {
            "DATA_SOURCE": os.environ.get("DATA_SOURCE"),
            "F1_YEAR": os.environ.get("F1_YEAR"),
        }
        try:
            os.environ["DATA_SOURCE"] = "local"
            os.environ["F1_YEAR"] = "2026"
            response = lambda_handler({}, None)
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        body = json.loads(response["body"])
        self.assertIsInstance(body, dict)


if __name__ == "__main__":
    unittest.main()
