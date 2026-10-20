# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-20

### Added
- **Core Observability Stack**: Production-grade Docker Compose architecture with pinned versions (`prom/prometheus:v2.54.1`, `prom/snmp-exporter:v0.26.0`, `prom/alertmanager:v0.27.0`, `grafana/grafana:11.1.0`).
- **SNMP Simulator**: Fully reproducible Debian-based test target running Net-SNMP `snmpd`, exposing MIB-II `if_mib` metrics for interface testing without physical hardware.
- **Prometheus Alerting Rules**: Alert definitions in `config/prometheus/alert.rules.yml` for target down, interface down, high utilization, errors, discards, and slow scrape latency.
- **Alertmanager Routing**: Default routing with webhook sink placeholder and inhibition rules in `config/alertmanager/alertmanager.yml`.
- **Grafana Provisioning**: Automated datasource (`prometheus.yml`) and dashboard provider (`dashboards.yml`) with pre-built `network-overview.json` dashboard.
- **Statistical Anomaly Detection**: Pure Python package in `src/anomaly_detector/` with Rolling Z-Score and EWMA detectors, Prometheus HTTP API client, and CLI interface.
- **Validation Suite & CI**: Cross-platform Python validator (`scripts/validate.py`), unit tests (`tests/test_anomaly_detector.py`, `tests/test_configs.py`), and GitHub Actions workflow (`.github/workflows/ci.yml`).
- **Academic Thesis Documentation**:
  - `docs/architecture.md`: Detailed component breakdown, data flow, ports, and security posture.
  - `docs/design-decisions.md`: Qualitative comparative trade-off analysis against Zabbix, LibreNMS, and Nagios.
  - `docs/evaluation-plan.md`: Research questions, measurement methodology, and empirical data tables with `[TODO]` placeholders.
  - `docs/setup-lab.md`: Step-by-step setup and troubleshooting guide.
- **Repository Governance**: `CITATION.cff`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE` (MIT), `.editorconfig`.
- **Legacy Lab Archive**: Relocated initial Zabbix exploratory prototype to `legacy/zabbix-lab/` for historical continuity.
