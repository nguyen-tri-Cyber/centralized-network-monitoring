#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}/deploy"

if [ ! -f .env ]; then
    echo "[INFO] No .env found in deploy/. Copying from .env.example..."
    cp .env.example .env
fi

echo "[INFO] Starting Centralized Network Monitoring stack..."
docker compose up -d --build

echo ""
echo "=== Stack Services Status ==="
docker compose ps

echo ""
echo "Access URLs:"
echo "  - Prometheus:    http://localhost:9090"
echo "  - Grafana:       http://localhost:3000 (default: admin / admin_lab_change_me)"
echo "  - Alertmanager:  http://localhost:9093"
echo "  - SNMP Exporter: http://localhost:9116"
