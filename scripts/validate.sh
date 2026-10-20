#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Running Validation Script ==="
python3 "${SCRIPT_DIR}/validate.py"

if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo "=== Running docker compose config ==="
    docker compose -f "${REPO_ROOT}/deploy/docker-compose.yml" config -q
    echo "[PASS] docker compose config valid."

    echo "=== Running promtool validation ==="
    docker run --rm \
      -v "${REPO_ROOT}/config/prometheus:/etc/prometheus:ro" \
      prom/prometheus:v2.54.1 \
      promtool check config /etc/prometheus/prometheus.yml
    docker run --rm \
      -v "${REPO_ROOT}/config/prometheus:/etc/prometheus:ro" \
      prom/prometheus:v2.54.1 \
      promtool check rules /etc/prometheus/alert.rules.yml
    echo "[PASS] promtool checks passed."
fi
