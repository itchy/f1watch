import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import boto3

EVENT_NAME_MAP = {
    "Pre Season Testing 1": "Sakhir",
    "Pre Season Testing 2": "Sakhir",
}

SESSION_LIVE_MINUTES = {
    "FP1": 60,
    "FP2": 60,
    "FP3": 60,
    "Q": 60,
    "SQ": 60,
    "Sprint": 60,
    "Grand Prix": 120,
    "Day 2": 240,
    "Day 3": 240,
    "Chequered Flag": 240,
}

LAST_GOOD_PAYLOAD = None
LAST_GOOD_GENERATED_AT = None


def _normalize_token(value: str) -> str:
    return "".join(char for char in str(value).lower() if char.isalnum())


def _parse_start(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    except (TypeError, ValueError):
        return None


def _load_json_from_s3(s3_client, bucket: str, key: str):
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read()), obj["LastModified"].astimezone(timezone.utc)


def _load_json_from_local(key: str):
    path = Path(key)
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return payload, modified


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
        sessions, sessions_modified = _load_json_from_s3(s3_client, bucket, keys["sessions"])
        teams, teams_modified = _load_json_from_s3(s3_client, bucket, keys["teams"])
        drivers, drivers_modified = _load_json_from_s3(s3_client, bucket, keys["drivers"])
    else:
        sessions, sessions_modified = _load_json_from_local(keys["sessions"])
        teams, teams_modified = _load_json_from_local(keys["teams"])
        drivers, drivers_modified = _load_json_from_local(keys["drivers"])

    data_last_updated = max(sessions_modified, teams_modified, drivers_modified)
    return sessions, teams, drivers, data_last_updated


def _duration(tdelta: timedelta) -> str:
    total_seconds = int(tdelta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"
    if total_seconds <= 3600:
        return f"{math.ceil(total_seconds / 60)}m"
    if total_seconds >= 86400:
        return f"{total_seconds // 86400}d"
    return f"{math.ceil(total_seconds / 3600)}h"


def _delta(start: datetime, now: datetime) -> str:
    if now < start:
        return _duration(start - now)
    return "LIVE"


def _session_live_window(session_name: str) -> timedelta:
    minutes = SESSION_LIVE_MINUTES.get(session_name, 60)
    return timedelta(minutes=minutes)


def _driver_abbreviation(driver: dict) -> str:
    return (
        driver["first_name"].lower()[0]
        + driver["last_name"].lower()[0]
        + str(driver["car_number"])
    )


def _request_url(event) -> str:
    event = event or {}
    headers = event.get("headers") or {}
    host = headers.get("x-forwarded-host") or headers.get("host") or "f1.itchy7.com"
    path = event.get("rawPath") or "/"
    raw_query = event.get("rawQueryString")
    if raw_query is None:
        raw_query = urlencode((event.get("queryStringParameters") or {}), doseq=True)
    if raw_query:
        return f"https://{host}{path}?{raw_query}"
    return f"https://{host}{path}"


def _query_params(event):
    return (event or {}).get("queryStringParameters") or {}


def _select_constructor(constructors, team_filter: str):
    if not team_filter:
        return None
    target = _normalize_token(team_filter)
    for constructor in constructors:
        if _normalize_token(constructor.get("name", "")) == target:
            return constructor
    return None


def _select_driver(driver_rows, driver_filter: str):
    if not driver_filter:
        return None
    target = _normalize_token(driver_filter)
    for driver in driver_rows:
        tokens = (
            driver.get("abbr", ""),
            driver.get("car_number", ""),
            f"{driver.get('first_name', '')}{driver.get('last_name', '')}",
            driver.get("last_name", ""),
        )
        if any(_normalize_token(token) == target for token in tokens):
            return driver
    return None


def _build_next_payload(
    sessions,
    teams,
    drivers,
    local_tz,
    tz_label: str,
    request_url: str,
    data_last_updated: datetime,
    team_filter: str | None = None,
    driver_filter: str | None = None,
):
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
        live_window = _session_live_window(session.get("session"))
        if now <= start + live_window:
            chosen = dict(session)
            chosen["event"] = EVENT_NAME_MAP.get(chosen.get("event"), chosen.get("event"))
            chosen_start = start
            break

    if not chosen or not chosen_start:
        return {"error": "No upcoming session found"}

    local_start = chosen_start.astimezone(local_tz)
    schedule = {
        "event": chosen.get("event"),
        "session": chosen.get("session"),
        "start": chosen_start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dow": local_start.strftime("%a"),
        "dom": str(local_start.day),
        "delta": _delta(chosen_start, now),
    }
    constructors = [
        {"name": team["team_name"], "place": str(team["place"])}
        for team in sorted(teams, key=lambda item: int(item["place"]))
    ]
    driver_rows = [
        {
            "abbr": _driver_abbreviation(driver),
            "first_name": driver["first_name"],
            "last_name": driver["last_name"],
            "car_number": str(driver["car_number"]),
            "place": str(driver["place"]),
        }
        for driver in sorted(drivers, key=lambda item: int(item["place"]))
    ]

    return {
        "general": {
            "source": "f1.itchy7.com",
            "request_url": request_url,
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timezone": tz_label,
            "data_last_updated_at": data_last_updated.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data_age_seconds": max(0, int((now - data_last_updated).total_seconds())),
            "using_last_good": False,
            "refresh": 60,
        },
        "schedule": schedule,
        "drivers": driver_rows,
        "constructors": constructors,
        "selected_driver": _select_driver(driver_rows, driver_filter),
        "selected_constructor": _select_constructor(constructors, team_filter),
    }


def _resolve_local_tz(event):
    params = _query_params(event)
    tz_name = params.get("tz") or os.environ.get("LOCAL_TZ", "America/Denver")
    try:
        return ZoneInfo(tz_name), tz_name
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"invalid tz: {tz_name}") from exc


def get_next_payload(event=None):
    year = os.environ.get("F1_YEAR", "2026")
    data_source = os.environ.get("DATA_SOURCE", "auto").lower()
    bucket = os.environ.get("DATA_BUCKET")
    local_tz, tz_label = _resolve_local_tz(event)
    request_url = _request_url(event)
    params = _query_params(event)
    team_filter = params.get("team")
    driver_filter = params.get("driver")

    sessions, teams, drivers, data_last_updated = _load_inputs(year, data_source, bucket)
    return _build_next_payload(
        sessions,
        teams,
        drivers,
        local_tz,
        tz_label,
        request_url,
        data_last_updated,
        team_filter=team_filter,
        driver_filter=driver_filter,
    )


def _fallback_payload_from_last_good(exc: Exception):
    if LAST_GOOD_PAYLOAD is None or LAST_GOOD_GENERATED_AT is None:
        return None
    payload = json.loads(json.dumps(LAST_GOOD_PAYLOAD))
    general = payload.setdefault("general", {})
    now = datetime.now(timezone.utc)
    general["generated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    general["using_last_good"] = True
    general["fallback_reason"] = str(exc)
    general["last_good_age_seconds"] = max(
        0, int((now - LAST_GOOD_GENERATED_AT).total_seconds())
    )
    return payload


def lambda_handler(event, context):
    global LAST_GOOD_PAYLOAD
    global LAST_GOOD_GENERATED_AT
    try:
        payload = get_next_payload(event)
        LAST_GOOD_PAYLOAD = payload
        LAST_GOOD_GENERATED_AT = datetime.now(timezone.utc)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=0, s-maxage=30, stale-while-revalidate=30",
            },
            "body": json.dumps(payload),
        }
    except ValueError as exc:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }
    except Exception as exc:
        fallback_payload = _fallback_payload_from_last_good(exc)
        if fallback_payload is not None:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Cache-Control": "public, max-age=0, s-maxage=30, stale-while-revalidate=30",
                },
                "body": json.dumps(fallback_payload),
            }
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }


if __name__ == "__main__":
    print(json.dumps(get_next_payload()))
