# Legacy Zabbix Lab Prototype Archive

## Overview

This directory preserves the preliminary experimental prototype developed during the exploratory phase of the undergraduate thesis (*Đề tài A1 - Hệ thống giám sát và cảnh báo mạng tập trung*).

The initial prototype utilized:
- **Core Engine**: Zabbix Server 7.4 with PostgreSQL 16
- **Web UI**: Zabbix Web Nginx
- **Collection**: Zabbix Agent 2, Net-SNMP container, ICMP ping
- **Automation & CLI**: Python 3.12 script (`a1.py`) and module (`a1lab/`) using the Zabbix JSON-RPC API
- **Testing & Scenarios**: Automated test suite TC01–TC12 with fault injection into containers

## Context & Thesis Transition

This codebase is preserved intact for historical reference, comparative benchmarking, and thesis auditability.

As documented in [docs/design-decisions.md](../../docs/design-decisions.md), the thesis transitioned to the Prometheus + Grafana + SNMP Exporter stack to achieve:
1. Declarative GitOps infrastructure without storing configuration in a stateful relational database.
2. Lightweight multi-dimensional label querying via PromQL.
3. Modular integration with the statistical anomaly detection module.

## Running the Legacy Prototype

If you wish to run or inspect the legacy Zabbix lab:

```powershell
# In Windows PowerShell:
.\setup.ps1 -Start
py -3.12 .\a1.py provision
py -3.12 .\a1.py verify
py -3.12 -m unittest discover -s tests -v
```

See [docs/OPERATIONS.md](docs/OPERATIONS.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full historical operations details.
