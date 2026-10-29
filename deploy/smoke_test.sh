#!/usr/bin/env bash
set -euo pipefail

url="${TASTEWELL_URL:-http://localhost:8080}"
: "${ACCESS_USER:?Set ACCESS_USER}"
: "${ACCESS_PASSWORD:?Set ACCESS_PASSWORD}"

unauthenticated=$(curl -sS -o /dev/null -w '%{http_code}' "$url/api/health")
test "$unauthenticated" = "401"
curl -fsS -u "$ACCESS_USER:$ACCESS_PASSWORD" "$url/api/health" | grep -q '"status":"ok"'
curl -fsS -u "$ACCESS_USER:$ACCESS_PASSWORD" "$url/decision" | grep -qi '<!DOCTYPE html'
qloo_status=$(curl -fsS --max-time 65 -u "$ACCESS_USER:$ACCESS_PASSWORD" "$url/api/qloo/status")
if ! grep -Eq '"ready"[[:space:]]*:[[:space:]]*true' <<<"$qloo_status"; then
  echo "Tastewell Qloo readiness check failed: $qloo_status" >&2
  exit 1
fi
echo "Tastewell private preview and Qloo readiness smoke passed"

