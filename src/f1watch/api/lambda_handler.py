import json
import os
from datetime import datetime, timedelta, timezone

import boto3


def _parse_start(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    except (TypeError, ValueError):
        return None


def _load_json_from_s3(s3_client, bucket: str, key: str):
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read())


def _load_json_from_local(key: str):
    with open(key, "r", encoding="utf-8") as file:
        return json.load(file)


def _load_inputs(year: str, data_source: str, bucket: str):
    keys = {
        "sessions": f"{year}_schedule.json",
        "teams": f"{year}_teams.json",
        "drivers": f"{year}_drivers.json",
    }

    use_s3 = data_source == "s3" or (data_source == "auto" and bucket)
    if use_s3:
        if not bucket:
            raise ValueError("DATA_BUCKET is required when DATA_SOURCE=s3")
        s3_client = boto3.client("s3")
        return (
            _load_json_from_s3(s3_client, bucket, keys["sessions"]),
            _load_json_from_s3(s3_client, bucket, keys["teams"]),
            _load_json_from_s3(s3_client, bucket, keys["drivers"]),
        )

    return (
        _load_json_from_local(keys["sessions"]),
        _load_json_from_local(keys["teams"]),
        _load_json_from_local(keys["drivers"]),
    )


def _duration(tdelta: timedelta) -> str:
    days = tdelta.days
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _delta(start: datetime, now: datetime) -> str:
    if now < start:
        return _duration(start - now)
    return "Live"


def _build_next_payload(sessions, teams, drivers, tz_offset_hours: int):
    now = datetime.now(timezone.utc)

    parsed_sessions = []
    for session in sessions:
        start = _parse_start(session.get("start"))
        if start is None:
            continue
        parsed_sessions.append((start, session))

    parsed_sessions.sort(key=lambda pair: pair[0])

    chosen = None
    chosen_start = None
    for start, session in parsed_sessions:
        if now - timedelta(hours=2) < start:
            chosen = dict(session)
            chosen_start = start
            break

    if not chosen or not chosen_start:
        return {"error": "No upcoming session found"}

    local_start = chosen_start + timedelta(hours=tz_offset_hours)
    chosen["dow"] = local_start.strftime("%a")
    chosen["dom"] = str(local_start.day)
    chosen["delta"] = _delta(chosen_start, now)

    for team in teams:
        chosen[team["team_name"].lower()] = team["place"]

    for driver in drivers:
        abr = (
            driver["first_name"].lower()[0]
            + driver["last_name"].lower()[0]
            + str(driver["car_number"])
        )
        chosen[abr] = driver["place"]

    return chosen


def get_next_payload():
    year = os.environ.get("F1_YEAR", "2026")
    data_source = os.environ.get("DATA_SOURCE", "auto").lower()
    bucket = os.environ.get("DATA_BUCKET")
    tz_offset_hours = int(os.environ.get("LOCAL_TZ_OFFSET_HOURS", "-7"))

    sessions, teams, drivers = _load_inputs(year, data_source, bucket)
    return _build_next_payload(sessions, teams, drivers, tz_offset_hours)


def lambda_handler(event, context):
    try:
        payload = get_next_payload()
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload),
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }


if __name__ == "__main__":
    print(json.dumps(get_next_payload()))
