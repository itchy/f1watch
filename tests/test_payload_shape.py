import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from f1watch.api.lambda_handler import (  # noqa: E402
    _build_next_payload,
    _duration,
    _fallback_payload_from_last_good,
    _resolve_local_tz,
    _request_url,
    lambda_handler,
)


class TestDataShape(unittest.TestCase):
    def test_duration_formats_23h_as_hours(self):
        self.assertEqual(_duration(timedelta(hours=23)), "23h")

    def test_duration_formats_24h_as_days(self):
        self.assertEqual(_duration(timedelta(hours=24)), "1d")

    def test_duration_rounds_up_hours_for_sub_day_countdown(self):
        self.assertEqual(_duration(timedelta(hours=5, minutes=20)), "6h")

    def test_duration_formats_one_hour_as_60_minutes(self):
        self.assertEqual(_duration(timedelta(hours=1)), "60m")

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
            request_url="https://f1.itchy7.com/?tz=UTC",
            data_last_updated=datetime.now(timezone.utc) - timedelta(minutes=5),
        )

        self.assertIsInstance(payload, dict)
        self.assertIn("general", payload)
        self.assertIn("schedule", payload)
        self.assertIn("drivers", payload)
        self.assertIn("constructors", payload)
        self.assertIn("selected_driver", payload)
        self.assertIn("selected_constructor", payload)
        self.assertEqual(payload["schedule"]["event"], "Test")
        self.assertEqual(payload["schedule"]["session"], "FP1")
        self.assertIn("dow", payload["schedule"])
        self.assertIn("dom", payload["schedule"])
        self.assertIn("delta", payload["schedule"])
        self.assertEqual(payload["constructors"][0]["name"], "McLaren")
        self.assertEqual(payload["constructors"][0]["place"], "1")
        self.assertEqual(payload["drivers"][0]["abbr"], "ln4")
        self.assertEqual(payload["drivers"][0]["place"], "1")
        self.assertIsNone(payload["selected_driver"])
        self.assertIsNone(payload["selected_constructor"])
        self.assertIn("data_age_seconds", payload["general"])
        self.assertGreaterEqual(payload["general"]["data_age_seconds"], 0)

    def test_payload_selection_fields_match_query_filters(self):
        sessions = [{"event": "Test", "session": "FP1", "start": "2099-01-01T10:00:00-00:00"}]
        teams = [
            {"team_name": "McLaren", "place": "1"},
            {"team_name": "Ferrari", "place": "2"},
        ]
        drivers = [
            {"first_name": "Lando", "last_name": "Norris", "car_number": "4", "place": "1"},
            {"first_name": "Lewis", "last_name": "Hamilton", "car_number": "44", "place": "2"},
        ]

        payload = _build_next_payload(
            sessions,
            teams,
            drivers,
            local_tz=ZoneInfo("UTC"),
            tz_label="UTC",
            request_url="https://f1.itchy7.com/?tz=UTC&team=mclaren&driver=ln4",
            data_last_updated=datetime.now(timezone.utc) - timedelta(minutes=5),
            team_filter="mclaren",
            driver_filter="ln4",
        )

        self.assertEqual(payload["selected_constructor"]["name"], "McLaren")
        self.assertEqual(payload["selected_driver"]["abbr"], "ln4")

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

    def test_query_param_tz_overrides_env(self):
        old_tz = os.environ.get("LOCAL_TZ")
        try:
            os.environ["LOCAL_TZ"] = "UTC"
            local_tz, tz_label = _resolve_local_tz(
                {"queryStringParameters": {"tz": "America/Los_Angeles"}}
            )
        finally:
            if old_tz is None:
                os.environ.pop("LOCAL_TZ", None)
            else:
                os.environ["LOCAL_TZ"] = old_tz

        self.assertEqual(getattr(local_tz, "key", None), "America/Los_Angeles")
        self.assertEqual(tz_label, "America/Los_Angeles")

    def test_env_local_tz_used_when_query_param_missing(self):
        old_tz = os.environ.get("LOCAL_TZ")
        try:
            os.environ["LOCAL_TZ"] = "America/New_York"
            local_tz, tz_label = _resolve_local_tz({})
        finally:
            if old_tz is None:
                os.environ.pop("LOCAL_TZ", None)
            else:
                os.environ["LOCAL_TZ"] = old_tz

        self.assertEqual(getattr(local_tz, "key", None), "America/New_York")
        self.assertEqual(tz_label, "America/New_York")

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

    def test_fallback_payload_from_last_good(self):
        import f1watch.api.lambda_handler as handler_module  # noqa: E402

        old_payload = handler_module.LAST_GOOD_PAYLOAD
        old_generated = handler_module.LAST_GOOD_GENERATED_AT
        try:
            handler_module.LAST_GOOD_PAYLOAD = {
                "general": {
                    "source": "f1.itchy7.com",
                    "request_url": "https://f1.itchy7.com/",
                    "generated_at": "2026-03-06T00:00:00Z",
                    "timezone": "America/Denver",
                    "refresh": 60,
                    "data_age_seconds": 1,
                },
                "schedule": {"event": "Test", "session": "FP1", "start": "2099-01-01T10:00:00Z"},
                "drivers": [],
                "constructors": [],
            }
            handler_module.LAST_GOOD_GENERATED_AT = datetime.now(timezone.utc) - timedelta(
                seconds=10
            )
            payload = _fallback_payload_from_last_good(RuntimeError("boom"))
        finally:
            handler_module.LAST_GOOD_PAYLOAD = old_payload
            handler_module.LAST_GOOD_GENERATED_AT = old_generated

        self.assertIsNotNone(payload)
        self.assertTrue(payload["general"]["using_last_good"])
        self.assertEqual(payload["general"]["fallback_reason"], "boom")
        self.assertGreaterEqual(payload["general"]["last_good_age_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
