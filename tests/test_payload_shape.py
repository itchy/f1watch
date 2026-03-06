import json
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from f1watch.api.lambda_handler import (  # noqa: E402
    _build_next_payload,
    _resolve_local_tz,
    _request_url,
    lambda_handler,
)


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

        payload = _build_next_payload(
            sessions,
            teams,
            drivers,
            local_tz=ZoneInfo("UTC"),
            tz_label="UTC",
            request_url="https://f1.itchy7.com/?offset=0",
        )

        self.assertIsInstance(payload, dict)
        self.assertIn("general", payload)
        self.assertIn("schedule", payload)
        self.assertIn("drivers", payload)
        self.assertIn("constructors", payload)
        self.assertEqual(payload["schedule"]["event"], "Test")
        self.assertEqual(payload["schedule"]["session"], "FP1")
        self.assertIn("dow", payload["schedule"])
        self.assertIn("dom", payload["schedule"])
        self.assertIn("delta", payload["schedule"])
        self.assertEqual(payload["constructors"][0]["name"], "McLaren")
        self.assertEqual(payload["constructors"][0]["place"], "1")
        self.assertEqual(payload["drivers"][0]["abbr"], "ln4")
        self.assertEqual(payload["drivers"][0]["place"], "1")

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

    def test_query_param_offset_overrides_env(self):
        old_offset = os.environ.get("LOCAL_TZ_OFFSET_HOURS")
        try:
            os.environ["LOCAL_TZ_OFFSET_HOURS"] = "-7"
            local_tz, tz_label = _resolve_local_tz({"queryStringParameters": {"offset": "2"}})
        finally:
            if old_offset is None:
                os.environ.pop("LOCAL_TZ_OFFSET_HOURS", None)
            else:
                os.environ["LOCAL_TZ_OFFSET_HOURS"] = old_offset

        self.assertEqual(local_tz.utcoffset(None).total_seconds(), 2 * 3600)
        self.assertEqual(tz_label, "UTC+2")

    def test_query_param_tz_overrides_offset(self):
        local_tz = _resolve_local_tz(
            {"queryStringParameters": {"tz": "America/Los_Angeles", "offset": "2"}}
        )
        self.assertEqual(getattr(local_tz[0], "key", None), "America/Los_Angeles")

    def test_invalid_offset_returns_400(self):
        old_env = {
            "DATA_SOURCE": os.environ.get("DATA_SOURCE"),
            "F1_YEAR": os.environ.get("F1_YEAR"),
        }
        try:
            os.environ["DATA_SOURCE"] = "local"
            os.environ["F1_YEAR"] = "2026"
            response = lambda_handler({"queryStringParameters": {"offset": "abc"}}, None)
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(response["statusCode"], 400)

    def test_invalid_tz_returns_400(self):
        old_env = {
            "DATA_SOURCE": os.environ.get("DATA_SOURCE"),
            "F1_YEAR": os.environ.get("F1_YEAR"),
        }
        try:
            os.environ["DATA_SOURCE"] = "local"
            os.environ["F1_YEAR"] = "2026"
            response = lambda_handler({"queryStringParameters": {"tz": "Mars/Phobos"}}, None)
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(response["statusCode"], 400)

    def test_request_url_builds_from_host_and_query(self):
        url = _request_url(
            {
                "headers": {"host": "f1.itchy7.com"},
                "rawPath": "/",
                "queryStringParameters": {"tz": "America/Los_Angeles"},
            }
        )
        self.assertEqual(url, "https://f1.itchy7.com/?tz=America%2FLos_Angeles")


if __name__ == "__main__":
    unittest.main()
