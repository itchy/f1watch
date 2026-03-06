# f1watch

Fun side project for generating F1 data and serving a compact "next event" payload for watch widgets.

## Architecture (4 elements)

1. Drivers scraper: `/Users/scott/code/f1/src/f1watch/scrapers/drivers.py`
2. Teams scraper: `/Users/scott/code/f1/src/f1watch/scrapers/teams.py`
3. Schedule scraper: `/Users/scott/code/f1/src/f1watch/scrapers/schedule.py`
4. API/Lambda reader: `/Users/scott/code/f1/src/f1watch/api/lambda_handler.py`

AWS Lambda entrypoint shim:

- `/Users/scott/code/f1/lambda_function.py` (exports `lambda_handler`)

Legacy notebooks are preserved in `/Users/scott/code/f1/archive/`, but scripts are now the primary path.

## Requirements

Python 3.10+.

Install dependencies:

```bash
pip install -r /Users/scott/code/f1/requirements.txt
```

## Data outputs

Generated files:

- `<year>_drivers.json`
- `<year>_teams.json`
- `<year>_schedule.json`

## Run scrapers manually

From repo root:

```bash
PYTHONPATH=src python -m f1watch.scrapers.drivers --year 2026
PYTHONPATH=src python -m f1watch.scrapers.teams --year 2026
PYTHONPATH=src python -m f1watch.scrapers.schedule --year 2026
```

## Scrape + upload to S3

Use:

- `/Users/scott/code/f1/scripts/scrape_and_upload.sh`
- `/Users/scott/code/f1/scripts/update_data.sh` (recommended; performs SSO login then scrape+upload)

Quick update command:

```bash
cd /Users/scott/code/f1
./scripts/update_data.sh
```

Example:

```bash
DATA_BUCKET=f1-data-00000000 F1_YEAR=2026 /Users/scott/code/f1/scripts/scrape_and_upload.sh
```

Dry run:

```bash
/Users/scott/code/f1/scripts/scrape_and_upload.sh --bucket f1-data-00000000 --year 2026 --dry-run
```

## Lambda/API behavior

`lambda_handler` loads the 3 JSON files from S3 or local, computes the next session, and returns one JSON payload.

API usage:

- Method: `GET`
- Path: `/`
- Query param: `tz` (optional IANA timezone name, for example `America/Los_Angeles`)

Example:

```bash
curl "https://f1.itchy7.com/"
curl "https://f1.itchy7.com/?tz=America/Los_Angeles"
```

Response shape is organized into sections:

- `general` (request metadata, generation timestamp, timezone, refresh)
- `schedule` (event/session/start/dow/dom/delta)
- `drivers` (array of driver objects)
- `constructors` (array of constructor objects)

OpenAPI spec:

- `/Users/scott/code/f1/openapi.yaml`

Environment variables:

- `F1_YEAR` default `2026`
- `DATA_SOURCE` values: `s3`, `local`, `auto` (default)
- `DATA_BUCKET` required if `DATA_SOURCE=s3`
- `LOCAL_TZ` default `America/Denver`

Expected S3 keys:

- `<F1_YEAR>_drivers.json`
- `<F1_YEAR>_teams.json`
- `<F1_YEAR>_schedule.json`

## Tests

Run:

```bash
python -m unittest discover -s /Users/scott/code/f1/tests -p 'test_*.py'
```

## Terraform (IaC)

Terraform scaffolding for AWS resources is in:

- `/Users/scott/code/f1/infra`

Start with `/Users/scott/code/f1/infra/README.md` for import-first setup.

## Notes

- Scraping is dependent on Formula1.com page markup and can break if selectors/classes change.
- If no future session is available, the API returns `{"error":"No upcoming session found"}`.
