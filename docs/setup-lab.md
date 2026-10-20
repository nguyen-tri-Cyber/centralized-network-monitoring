# Step-by-Step Laboratory Setup Guide

## 1. System Requirements and Prerequisites

Before setting up the laboratory environment, ensure your workstation meets the following prerequisites:

- **Operating System**: Windows 10/11 (with WSL2 enabled), Linux (Ubuntu 20.04+, Debian 11+, Fedora 38+), or macOS (12+).
- **Docker Engine**: Docker 20.10+ and Docker Compose v2.0+ (included with Docker Desktop).
- **Python**: Python 3.10, 3.11, or 3.12 (with `pip`).
- **Disk & Memory**: At least 4 GB available RAM and 10 GB free disk space.
- **Port Availability**: Verify that host ports `9090` (Prometheus), `3000` (Grafana), `9093` (Alertmanager), `9116` (SNMP Exporter), and `161/udp` (SNMP) are not currently bound by other local services.

---

## 2. Quick Setup Instructions

### Option A: Using Helper Scripts (Recommended)

#### On Linux / macOS:
```bash
# 1. Clone the repository and navigate to root
cd centralized-network-monitoring

# 2. Launch the stack
bash scripts/up.sh
```

#### On Windows (PowerShell):
```powershell
# 1. Open PowerShell in repository root
Set-Location -Path centralized-network-monitoring

# 2. Run the startup script
powershell -ExecutionPolicy Bypass -File .\scripts\up.ps1
```

### Option B: Using Makefile (Linux / macOS / WSL)
```bash
make up
```

### Option C: Direct Docker Compose Commands
```bash
cd deploy
cp .env.example .env
docker compose up -d --build
```

---

## 3. Verifying the Running Environment

Once the stack is initialized, verify that all services are operational:

1. **Prometheus Web UI**: Open [http://localhost:9090](http://localhost:9090)
   - Navigate to **Status** → **Targets**.
   - Verify that all three scrape jobs (`prometheus`, `snmp_exporter`, and `snmp`) display state **UP**.
2. **Grafana Dashboards**: Open [http://localhost:3000](http://localhost:3000)
   - Log in with default credentials: User `admin`, Password `admin_lab_change_me` (or configured in `.env`).
   - Navigate to **Dashboards** → **Network Observability** → **Network Observability - SNMP Overview**.
   - Confirm that panels render live data: SNMP Scrape Status (UP), System Uptime, Interface In/Out throughput.
3. **Alertmanager Web UI**: Open [http://localhost:9093](http://localhost:9093)
   - Confirm that Alertmanager is running and healthy.
4. **SNMP Exporter Raw Endpoint**: Open [http://localhost:9116](http://localhost:9116)
   - Test scraping the simulator manually:
     [http://localhost:9116/snmp?target=snmp-simulator:161&module=if_mib](http://localhost:9116/snmp?target=snmp-simulator:161&module=if_mib)

---

## 4. Running Validation and Test Suites

To verify configurations, linting, and unit tests without launching the containers:

```bash
# Run cross-platform Python validator
python scripts/validate.py

# Or run unit tests directly
python -m unittest discover -s tests -v
```

---

## 5. Simulating Network Faults in the Lab

To test Prometheus alerting and Grafana visualization during failure conditions:

### 5.1 Simulate Device Down (Outage)
```bash
# Stop the SNMP target container
docker stop snmp-simulator

# Within 1-2 minutes:
# 1. Prometheus Status -> Targets will show target state as DOWN.
# 2. Alert 'SNMPTargetDown' will transition from PENDING to FIRING.
# 3. Grafana status indicator will turn RED (DOWN).

# Restore the target
docker start snmp-simulator
```

### 5.2 Test Anomaly Detection Module
```bash
# Run statistical anomaly detection against Prometheus metrics
python -m src.anomaly_detector.cli \
  --prometheus-url http://localhost:9090 \
  --query 'rate(ifHCInOctets{job="snmp"}[1m]) * 8' \
  --algorithm zscore \
  --threshold 3.0
```

---

## 6. Troubleshooting Common Issues

### 6.1 Docker Daemon Not Reachable
- **Symptom**: `failed to connect to the docker API at ...`
- **Solution**: Ensure Docker Desktop is launched and running. On Windows, verify that "Use the WSL 2 based engine" is enabled in Docker Desktop settings.

### 6.2 Host Port Already in Use
- **Symptom**: `bind: address already in use` for port `3000` or `9090`.
- **Solution**: Edit `.env` in `deploy/` and assign alternative host ports, for example:
  ```dotenv
  PROMETHEUS_PORT=9095
  GRAFANA_PORT=3005
  ```

### 6.3 SNMP Target Shows DOWN (`up == 0`)
- **Symptom**: Prometheus target `snmp` is DOWN with error `error reading from socket: connection refused` or timeout.
- **Solution**:
  1. Check if `snmp-simulator` is running: `docker ps --filter name=snmp-simulator`.
  2. Inspect container logs: `docker logs snmp-simulator`.
  3. Verify community string matches between `.env` and `config/snmp/snmp.yml`. Default is `public`.

### 6.4 Grafana Dashboard Shows "No Data"
- **Symptom**: Grafana panels show "No data" even though Prometheus is running.
- **Solution**:
  1. Verify the Prometheus datasource URL in Grafana is `http://prometheus:9090`.
  2. Ensure Prometheus has completed at least 2 scrape cycles (30 seconds) to compute `rate(...)` functions.
  3. Change the Grafana dashboard time picker to "Last 15 minutes" with auto-refresh set to "10s".
