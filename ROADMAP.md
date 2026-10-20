# Project Roadmap

This roadmap outlines the development milestones and planned research directions for the Centralized Network Monitoring System.

## Milestone 1: Core Observability Stack (Current Release - v1.0.0)

- [x] Docker Compose stack with pinned container images (`prometheus:v2.54.1`, `snmp-exporter:v0.26.0`, `alertmanager:v0.27.0`, `grafana:11.1.0`).
- [x] SNMPv2c simulator container (`debian:bookworm-slim` with Net-SNMP) providing standard MIB-II `if_mib` metrics.
- [x] Prometheus alert rules for device reachability, interface down, traffic saturation, packet errors, discards, and scrape latency.
- [x] Automated Grafana provisioning with pre-configured Prometheus datasource and interactive Network Overview dashboard.
- [x] Statistical anomaly detection module implementing Rolling Z-Score and EWMA algorithms with synthetic test suite.
- [x] Automated validation tooling (`scripts/validate.py`) and GitHub Actions CI workflow (`.github/workflows/ci.yml`).
- [x] Comprehensive thesis documentation (`architecture.md`, `design-decisions.md`, `evaluation-plan.md`, `setup-lab.md`).

---

## Milestone 2: Laboratory Evaluation & Benchmarks (Planned)

- [ ] Complete empirical benchmarks defined in `docs/evaluation-plan.md` on physical network hardware `[TODO: author to measure in physical lab]`.
- [ ] Measure detection latency ($T_{\text{det}}$) and notification dispatch latency across varying scrape intervals (15s, 30s, 60s).
- [ ] Evaluate false alarm rate (FAR) under synthetic transient micro-burst scenarios.
- [ ] Incorporate Alertmanager webhook integration with realistic communication sinks (e.g., Discord or Slack incoming webhooks).

---

## Milestone 3: Security & Enterprise Protocol Hardening (Planned)

- [ ] Add SNMPv3 User-based Security Model (USM) support with SHA256 authentication and AES128 privacy encryption.
- [ ] Implement reverse proxy with TLS termination (Nginx or Caddy) to secure Grafana and Prometheus web interfaces.
- [ ] Provide Role-Based Access Control (RBAC) guidance for multi-tenant campus networks.

---

## Milestone 4: Advanced Telemetry & Next-Gen Protocols (Future Work)

- [ ] Evaluate gNMI (gRPC Network Management Interface) and streaming telemetry as a high-frequency alternative to SNMP polling.
- [ ] Explore hybrid anomaly detection combining EWMA with seasonal decomposition (STL) for weekly cyclical patterns.
- [ ] Kubernetes Helm chart packaging for cloud-native campus deployment.
