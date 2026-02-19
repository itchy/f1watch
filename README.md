# f1

Utilities and notebook workflows for generating Formula 1 datasets used by widgets/scripts.

## What this repo contains

- `2026_schedule.json`: Session-level schedule data (`event`, `session`, `start`).
- `2026_teams.json`: Constructor standings snapshot.
- `2026_drivers.json`: Driver standings snapshot plus `car_number`.
- `next.ipynb`: Produces one JSON object describing the next session plus team/driver ranking keys.
- `_schedules.ipynb`: Scrapes schedule/session details from Formula1.com and writes `<year>_schedule.json`.
- `_teams.ipynb`: Scrapes team standings and writes `<year>_teams.json`.
- `_drivers.ipynb`: Scrapes driver standings, resolves car numbers, and writes `<year>_drivers.json`.
- `data/`: Historical snapshots for 2025.

## Requirements

Python 3.10+ is recommended.

Install dependencies:

```bash
pip install requests beautifulsoup4 boto3
```

Notes:
- `boto3` is only needed if you switch `next.ipynb` from local files to S3 reads.

## How to regenerate data

1. Open `_drivers.ipynb`, `_teams.ipynb`, and `_schedules.ipynb`.
2. Set `year` in each notebook.
3. Run each notebook end-to-end.
4. Confirm files were generated:

```bash
ls -1 *_drivers.json *_teams.json *_schedule.json
```

## Data format

### Drivers (`<year>_drivers.json`)

```json
{
  "first_name": "Lando",
  "last_name": "Norris",
  "place": "1",
  "points": "423",
  "car_number": "4"
}
```

### Teams (`<year>_teams.json`)

```json
{
  "team_name": "McLaren",
  "place": "1",
  "points": "833"
}
```

### Schedule (`<year>_schedule.json`)

```json
{
  "event": "Melbourne",
  "session": "Grand Prix",
  "start": "2026-03-07T13:00:00-00:00"
}
```

## Running `next.ipynb`

`next.ipynb` expects these files in the repo root:

- `<year>_schedule.json`
- `<year>_teams.json`
- `<year>_drivers.json`

The output is a single JSON object for the next upcoming session, augmented with:

- Team rank keys (lowercased team names)
- Driver rank keys (initials + car number, e.g. `ln4`)
- Time helpers (`dow`, `dom`, `delta`)

## Lambda / S3 configuration

`next.ipynb` supports loading input JSON from S3 (for Lambda) or local files (for development).

Environment variables:

- `F1_YEAR` (default: `2026`)
- `DATA_SOURCE`:
  - `s3`: force S3 reads
  - `local`: force local file reads
  - `auto` (default): use S3 when `DATA_BUCKET` is set, else local
- `DATA_BUCKET`: S3 bucket name (required when `DATA_SOURCE=s3`)

Expected S3 object keys:

- `<F1_YEAR>_schedule.json`
- `<F1_YEAR>_teams.json`
- `<F1_YEAR>_drivers.json`

## Scrape + upload script

Use `/Users/scott/code/f1/scripts/scrape_and_upload.sh` to execute all scraping notebooks and upload refreshed data files to S3.

Example:

```bash
DATA_BUCKET=f1-data-00000000 F1_YEAR=2026 /Users/scott/code/f1/scripts/scrape_and_upload.sh
```

With optional prefix and dry run:

```bash
/Users/scott/code/f1/scripts/scrape_and_upload.sh --bucket f1-data-00000000 --year 2026 --prefix data --dry-run
```

## Known fragility / caveats

- Formula1.com HTML/CSS class names are scraped directly. If the site markup changes, notebook parsing may break.
- `next.ipynb` assumes schedule timestamps match `%Y-%m-%dT%H:%M:%S%z` exactly.
- Schedule ordering is assumed chronological when determining the next session.

## Suggested maintenance

- Add validation for timestamp format before writing schedule output.
- Add graceful error handling when scraping selectors are missing.
- Move notebook logic into versioned Python scripts for easier testing/automation.
