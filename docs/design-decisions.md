# Architectural Design Decisions and Technology Trade-offs

## 1. Overview and Problem Context

Centralized network monitoring in enterprise and campus networks has traditionally relied on monolithic, relational database-backed systems. For an undergraduate thesis on modern network observability, selecting an architecture requires balancing ease of deployment, data model expressiveness, scalability, and support for automated infrastructure-as-code (GitOps).

This document details the rationale behind selecting **SNMP + Prometheus + Grafana**, provides a qualitative comparative analysis against established alternatives (**Zabbix**, **LibreNMS**, and **Nagios**), and documents the project's architectural transition.

---

## 2. Comparative Analysis of Monitoring Architectures

The following matrix provides a qualitative comparison across architectural dimensions:

| Dimension | Prometheus + Grafana + snmp_exporter | Zabbix | LibreNMS | Nagios Core |
|---|---|---|---|---|
| **Core Architecture** | Decoupled microservices (TSDB, Exporter, Dashboard, Alert router) | Monolithic C daemon + relational database + PHP Web | Monolithic PHP/Python daemon + MySQL/MariaDB + Web | Central C scheduler + file-based plugins |
| **Data Model** | Multi-dimensional time-series with key-value labels | Metric items grouped by host, stored in relational tables | RRDtool files + relational inventory metadata | Status-oriented states (`OK`, `WARN`, `CRIT`) + perfdata strings |
| **Query Language** | PromQL (vector math, aggregations, rate calculations) | Custom trigger syntax / SQL backend queries | Fixed SQL views / predefined graph formulas | Script exit codes (`0`, `1`, `2`) |
| **Configuration Model** | Declarative YAML files (GitOps-friendly, version-controlled) | Web UI / XML/JSON export / relational DB state | Web UI / database state | File-based text definitions (`cfg` files) |
| **Alerting Model** | Decoupled Alertmanager (grouping, inhibition, routing, deduplication) | Action triggers inside monolith, escalation pipelines | Rule-based transport maps inside web interface | Periodic polling triggers, contact groups |
| **Dynamic Discovery** | Native service discovery (file, DNS, cloud/container APIs) | Active network discovery & Low-Level Discovery (LLD) | Auto-discovery via ARP/CDP/LLDP sweeps | Manual configuration or external scripts |
| **Long-term Storage** | High-density TSDB chunks, remote write support (Cortex/Thanos/M3) | Relational database (PostgreSQL/MySQL) with housekeeping | Relational DB + fixed-resolution RRD files | Flat files / RRDtool plugins |

---

## 3. Technology Trade-offs

### 3.1 Prometheus + Grafana Stack
- **Key Strengths**:
  - **Multi-dimensional Data Model**: Metrics like `ifHCInOctets` carry arbitrary dimensions (`instance`, `ifIndex`, `ifDescr`, `device_type`). Aggregating bandwidth across entire rack groups or device types requires a single PromQL expression (`sum by (device_type) (rate(...))`).
  - **GitOps and Reproducibility**: The entire monitoring infrastructure—scrape targets, alerting thresholds, provisioning datasources, and dashboards—is configured through declarative text files stored in version control.
  - **Lightweight Decoupled Services**: Storage, querying, and scraping operate as independent processes with low memory overhead per polled metric point.
- **Trade-offs & Constraints**:
  - Requires an external exporter (`snmp_exporter`) to bridge SNMP walks to HTTP exposition.
  - Does not provide a built-in interactive device inventory management UI out of the box (addressed by Grafana table panels).

### 3.2 Zabbix
- **Key Strengths**:
  - Rich out-of-the-box support for heterogeneous agents, SNMP, IPMI, and ICMP without external adapters.
  - Mature web GUI for ad-hoc configuration, user privilege management, and event acknowledgments.
- **Trade-offs & Constraints**:
  - Relational database backend (PostgreSQL/MySQL) requires database maintenance (table partitioning, vacuuming) as metric volume grows.
  - Managing configurations through the Web UI makes strict GitOps and version-controlled review workflows more cumbersome unless fully driven through the JSON-RPC API.

### 3.3 LibreNMS
- **Key Strengths**:
  - Specifically optimized for network devices: automatically discovers vendor-specific MIBs, routing tables (BGP/OSPF), and topology maps via LLDP/CDP.
- **Trade-offs & Constraints**:
  - Tightly coupled to network hardware monitoring; less suited as a generalized telemetry platform for application metrics and container infrastructure.
  - Relies on RRDtool for time-series graphing, which downsamples historical resolution and lacks mathematical ad-hoc aggregation across metrics.

### 3.4 Nagios
- **Key Strengths**:
  - Simple, battle-tested check model based on process exit codes (`0`, `1`, `2`, `3`).
- **Trade-offs & Constraints**:
  - Process-forking architecture creates significant CPU overhead when polling large numbers of SNMP metrics.
  - State-based rather than metric-based: inherently designed for threshold checks rather than continuous numeric observability and rate trend analysis.

---

## 4. Note on Laboratory Prototyping Evolution

During the preliminary phase of this research, an initial prototype was built using Zabbix 7.4, PostgreSQL, and Python automation scripts (preserved in `legacy/zabbix-lab/` for reference and reproducibility).

While the Zabbix prototype successfully validated simulated ICMP, Linux agent, and SNMP polling, it highlighted key operational considerations:
1. Orchestrating a relational database schema and web application server increased container startup times and resource usage.
2. Alert rules and dashboard layouts were bound to database state rather than immutable, reviewable YAML code.

The transition to Prometheus, `snmp_exporter`, and Grafana was made to adopt an open, cloud-native observability stack that natively supports declarative infrastructure, expressive vector queries via PromQL, and modular integration with external analytics engines like the statistical anomaly detector.
