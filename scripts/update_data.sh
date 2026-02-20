#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

PROFILE="${AWS_PROFILE:-f1-sso}"
YEAR="${F1_YEAR:-2026}"
BUCKET="${DATA_BUCKET:-f1-data-00000000}"

usage() {
  cat <<USAGE
Usage:
  scripts/update_data.sh [options]

Options:
  --profile <name>   AWS profile (default: $PROFILE)
  --year <year>      Data year (default: $YEAR)
  --bucket <bucket>  S3 bucket (default: $BUCKET)
  --no-login         Skip 'aws sso login'
  -h, --help         Show help
USAGE
}

DO_LOGIN="true"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --year)
      YEAR="$2"
      shift 2
      ;;
    --bucket)
      BUCKET="$2"
      shift 2
      ;;
    --no-login)
      DO_LOGIN="false"
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

if ! command -v aws >/dev/null 2>&1; then
  echo "Missing required command: aws" >&2
  exit 1
fi

if [[ "$DO_LOGIN" == "true" ]]; then
  echo "Logging in with AWS profile: $PROFILE"
  aws sso login --profile "$PROFILE"
fi

echo "Running scrape + upload (year=$YEAR, bucket=$BUCKET, profile=$PROFILE)"
DATA_BUCKET="$BUCKET" F1_YEAR="$YEAR" ./scripts/scrape_and_upload.sh --profile "$PROFILE"
