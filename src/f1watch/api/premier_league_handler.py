import json
from datetime import datetime, timedelta, timezone


def _minutes_to_next_refresh(now: datetime, interval_minutes: int) -> int:
    minute_slot = (now.minute // interval_minutes) * interval_minutes
    current_slot = now.replace(minute=minute_slot, second=0, microsecond=0)
    next_slot = current_slot + timedelta(minutes=interval_minutes)
    return max(0, int((next_slot - now).total_seconds() // 60))


def get_payload():
    now = datetime.now(timezone.utc)
    refresh_seconds = 60
    delta_minutes = _minutes_to_next_refresh(now, 15)
    return {
        "league": "Premier League",
        "event": "Template",
        "session": "Data Refresh",
        "start": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "delta": f"{delta_minutes}m",
        "refresh": refresh_seconds,
        "note": "Template endpoint. Replace with real PL fixtures and standings feed.",
    }


def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=0, s-maxage=30, stale-while-revalidate=30",
        },
        "body": json.dumps(get_payload()),
    }

