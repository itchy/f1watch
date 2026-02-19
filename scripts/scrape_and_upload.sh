#!/usr/bin/env bash
set -euo pipefail

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

if ! command -v jupyter >/dev/null 2>&1; then
  echo "Missing required command: jupyter" >&2
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

NOTEBOOKS=("_drivers.ipynb" "_teams.ipynb" "_schedules.ipynb")
OUTPUT_FILES=(
  "${YEAR}_drivers.json"
  "${YEAR}_teams.json"
  "${YEAR}_schedule.json"
)

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

for nb in "${NOTEBOOKS[@]}"; do
  if [[ ! -f "$nb" ]]; then
    echo "Notebook not found: $nb" >&2
    exit 1
  fi
  echo "Executing $nb"
  jupyter nbconvert --to notebook --execute "$nb" --output-dir "$TMP_DIR" --output "executed-$(basename "$nb")" >/dev/null

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
