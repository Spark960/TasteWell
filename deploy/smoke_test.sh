#!/usr/bin/env bash
set -euo pipefail

url="${TASTEWELL_URL:-http://localhost:8080}"
: "${ACCESS_USER:?Set ACCESS_USER}"
: "${ACCESS_PASSWORD:?Set ACCESS_PASSWORD}"

unauthenticated=$(curl -sS -o /dev/null -w '%{http_code}' "$url/api/health")
test "$unauthenticated" = "401"
curl -fsS -u "$ACCESS_USER:$ACCESS_PASSWORD" "$url/api/health" | grep -q '"status":"ok"'
curl -fsS -u "$ACCESS_USER:$ACCESS_PASSWORD" "$url/decision" | grep -qi '<!DOCTYPE html'
echo "Tastewell private preview smoke passed"

