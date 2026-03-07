import json
import os
from datetime import datetime, timezone

import boto3

from f1watch.scrapers.drivers import get_drivers
from f1watch.scrapers.schedule import get_f1_schedule
from f1watch.scrapers.teams import get_teams


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _target_year() -> int:
    return int(os.environ.get("F1_YEAR", str(_current_year())))


def _target_bucket() -> str:
    bucket = os.environ.get("DATA_BUCKET")
    if not bucket:
        raise ValueError("DATA_BUCKET is required")
    return bucket


def _write_json_to_s3(s3_client, bucket: str, key: str, payload) -> None:
    body = json.dumps(payload, indent=4) + "\n"
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/json",
    )


def run_scrape_publish() -> dict:
    year = _target_year()
    bucket = _target_bucket()
    s3_client = boto3.client("s3")

    drivers = get_drivers(year)
    teams = get_teams(year)
    schedule = get_f1_schedule(year)

    keys = {
        "drivers": f"{year}_drivers.json",
        "teams": f"{year}_teams.json",
        "schedule": f"{year}_schedule.json",
    }

    _write_json_to_s3(s3_client, bucket, keys["drivers"], drivers)
    _write_json_to_s3(s3_client, bucket, keys["teams"], teams)
    _write_json_to_s3(s3_client, bucket, keys["schedule"], schedule)

    return {
        "year": year,
        "bucket": bucket,
        "keys": keys,
        "counts": {
            "drivers": len(drivers),
            "teams": len(teams),
            "schedule": len(schedule),
        },
    }


def lambda_handler(event, context):
    try:
        result = run_scrape_publish()
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }

