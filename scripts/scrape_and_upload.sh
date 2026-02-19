#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

usage() {
  cat <<'USAGE'
Usage:
  scripts/scrape_and_upload.sh [options]

Options:
  --year <year>        Year for output files (default: $F1_YEAR or 2026)
  --bucket <bucket>    S3 bucket name (default: $DATA_BUCKET)
  --prefix <prefix>    Optional S3 key prefix (example: data)
  --profile <profile>  Optional AWS CLI profile
  --region <region>    Optional AWS region
  --dry-run            Print actions without uploading
  -h, --help           Show this help

Environment defaults:
  F1_YEAR, DATA_BUCKET, AWS_PROFILE, AWS_REGION

Expected uploaded files:
  <year>_drivers.json
  <year>_teams.json
  <year>_schedule.json
USAGE
}

YEAR="${F1_YEAR:-2026}"
BUCKET="${DATA_BUCKET:-}"
PREFIX=""
DRY_RUN="false"
AWS_PROFILE_ARG="${AWS_PROFILE:-}"
AWS_REGION_ARG="${AWS_REGION:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --year)
      YEAR="$2"
      shift 2
      ;;
    --bucket)
      BUCKET="$2"
      shift 2
      ;;
    --prefix)
      PREFIX="$2"
      shift 2
      ;;
    --profile)
      AWS_PROFILE_ARG="$2"
      shift 2
      ;;
    --region)
      AWS_REGION_ARG="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$BUCKET" ]]; then
  echo "DATA_BUCKET is required. Set --bucket or DATA_BUCKET." >&2
  exit 1
fi

if ! command -v python >/dev/null 2>&1; then
  echo "Missing required command: python" >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "Missing required command: aws" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Missing required command: jq" >&2
  exit 1
fi

SCRAPER_MODULES=(
  "f1watch.scrapers.drivers"
  "f1watch.scrapers.teams"
  "f1watch.scrapers.schedule"
)
OUTPUT_FILES=(
  "${YEAR}_drivers.json"
  "${YEAR}_teams.json"
  "${YEAR}_schedule.json"
)

if [[ ! -d "src/f1watch" ]]; then
  echo "Expected package path missing: src/f1watch" >&2
  exit 1
fi

for module in "${SCRAPER_MODULES[@]}"; do
  echo "Executing ${module}"
  if ! PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" python -m "$module" --year "$YEAR" --output-dir "."; then
    echo "Failed while running scraper module: ${module}" >&2
    exit 1
  fi
done

for file in "${OUTPUT_FILES[@]}"; do
  if [[ ! -s "$file" ]]; then
    echo "Expected output file missing or empty: $file" >&2
    exit 1
  fi
  jq empty "$file" >/dev/null
  echo "Validated JSON: $file"
done

AWS_ARGS=()
if [[ -n "$AWS_PROFILE_ARG" ]]; then
  AWS_ARGS+=(--profile "$AWS_PROFILE_ARG")
fi
if [[ -n "$AWS_REGION_ARG" ]]; then
  AWS_ARGS+=(--region "$AWS_REGION_ARG")
fi

PREFIX_CLEAN="${PREFIX#/}"
PREFIX_CLEAN="${PREFIX_CLEAN%/}"

for file in "${OUTPUT_FILES[@]}"; do
  key="$file"
  if [[ -n "$PREFIX_CLEAN" ]]; then
    key="$PREFIX_CLEAN/$file"
  fi

  target="s3://${BUCKET}/${key}"

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[dry-run] aws ${AWS_ARGS[*]} s3 cp $file $target"
  else
    echo "Uploading $file -> $target"
    aws "${AWS_ARGS[@]}" s3 cp "$file" "$target"
  fi
done

echo "Done."
