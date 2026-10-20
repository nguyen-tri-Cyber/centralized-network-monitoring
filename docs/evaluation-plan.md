# Experimental Evaluation Plan and Methodology

## 1. Overview and Objectives

This document establishes the experimental methodology for evaluating the performance, accuracy, and operational overhead of the Centralized Network Monitoring System.

In accordance with strict academic integrity standards:
- This document defines the **research questions, measurement protocols, and experimental setups only**.
- It does **not** contain fabricated benchmark numbers or simulated measurements.
- All evaluation tables contain clear `[TODO: author to fill in real result]` placeholders to be completed by the thesis author following physical or simulated test execution.

---

## 2. Research Questions

- **RQ1 (Detection Latency)**: What is the end-to-end detection delay ($T_{\text{det}}$) from the moment a network fault occurs (device down or interface failure) until an alert transition is recorded by Prometheus and received by Alertmanager?
- **RQ2 (Alert Precision & Transient Resilience)**: How effectively do Prometheus evaluation intervals and alert durations (`for: 1m`, `for: 3m`) prevent false alarms caused by transient network spikes and momentary packet loss?
- **RQ3 (Monitoring Overhead)**: What is the computational overhead (CPU utilization, resident memory footprint, and SNMP scrape walk duration) of polling at high frequency (15 seconds) compared to standard frequency (60 seconds)?

---

## 3. Metrics and Mathematical Definitions

1. **Detection Delay ($T_{\text{det}}$)**:
   $$T_{\text{det}} = t_{\text{alert\_firing}} - t_{\text{fault\_injected}}$$
   Measured in seconds. Represents the latency between fault inception and Prometheus setting the alert state to `firing`.

2. **Notification Dispatch Latency ($T_{\text{notif}}$)**:
   $$T_{\text{notif}} = t_{\text{webhook\_received}} - t_{\text{alert\_firing}}$$
   Measured in seconds. Accounts for Alertmanager grouping wait (`group_wait: 10s`) and network dispatch time.

3. **Total Incident Awareness Time ($T_{\text{total}}$)**:
   $$T_{\text{total}} = T_{\text{det}} + T_{\text{notif}}$$

4. **False Alarm Rate (Transient Resilience)**:
   $$\text{FAR} = \frac{\text{False Positive Alerts}}{\text{Total Transient Injection Events}}$$

5. **Scrape Walk Duration**:
   Measured via the metric `snmp_scrape_duration_seconds` across repeated walk cycles.

---

## 4. Test Scenarios and Execution Protocols

### Scenario 1: Target Device Unreachable (Outage)
- **Protocol**:
  1. Record baseline timestamp $t_0$.
  2. Disconnect the target simulator container: `docker stop snmp-simulator` (or apply iptables DROP rule on UDP 161).
  3. Query Prometheus API for `ALERTS{alertname="SNMPTargetDown"}` until state is `firing` ($t_1$).
  4. Query Webhook receiver for dispatch timestamp ($t_2$).
  5. Restore the container (`docker start snmp-simulator`) and record recovery timestamp $t_3$.

### Scenario 2: Interface Operational State Change (Link Down)
- **Protocol**:
  1. Record baseline status of interface `eth0` (`ifOperStatus == 1`).
  2. Simulate link down inside container: `ip link set dev eth0 down`.
  3. Record time until `NetworkInterfaceDown` transitions to `firing`.
  4. Restore interface: `ip link set dev eth0 up` and record recovery time.

### Scenario 3: High Traffic / Bandwidth Saturation
- **Protocol**:
  1. Generate synthetic traffic exceeding 80% of rated interface bandwidth using `iperf3` or sustained packet flooding.
  2. Observe `rate(ifHCInOctets[1m]) * 8` in Prometheus.
  3. Record time until `HighInterfaceUtilization` transitions to `firing`.

### Scenario 4: Transient Micro-burst (Resilience Test)
- **Protocol**:
  1. Temporarily drop packets or induce a high latency burst for 5 seconds (< scrape interval).
  2. Verify whether the `for` duration constraint prevents spurious alerts from firing.

---

## 5. Experimental Data Capture Templates

### Table 5.1: Fault Detection and Notification Latency (RQ1)

*Note: All values must be recorded from actual laboratory test runs.*

| Trial ID | Test Scenario | Injection Time ($t_0$) | Prometheus Alert Fired ($t_1$) | Webhook Received ($t_2$) | $T_{\text{det}}$ (s) | $T_{\text{notif}}$ (s) | Total (s) | Status |
|---|---|---|---|---|---|---|---|---|
| TR-01 | Target Unreachable | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |
| TR-02 | Target Unreachable | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |
| TR-03 | Target Unreachable | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |
| TR-04 | Interface Down (`eth0`) | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |
| TR-05 | Interface Down (`eth0`) | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |
| TR-06 | Interface Down (`eth0`) | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |

---

### Table 5.2: Transient Noise and False Alarm Evaluation (RQ2)

| Trial ID | Disturbance Injected | Duration | Expected Alert State | Observed Alert State | Result |
|---|---|---|---|---|---|
| TN-01 | Drop packets for 5s | 5s | Suppressed (Pending) | `[TODO]` | `[TODO]` |
| TN-02 | Drop packets for 10s | 10s | Suppressed (Pending) | `[TODO]` | `[TODO]` |
| TN-03 | Traffic spike for 15s | 15s | Suppressed (Pending) | `[TODO]` | `[TODO]` |
| TN-04 | Traffic spike for 30s | 30s | Suppressed (Pending) | `[TODO]` | `[TODO]` |

---

### Table 5.3: Scrape Frequency vs. Resource Overhead (RQ3)

| Metric Polling Interval | Prometheus CPU (%) | Prometheus RAM (MB) | snmp_exporter CPU (%) | Average Scrape Duration (s) |
|---|---|---|---|---|
| 15 seconds (High Frequency) | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |
| 30 seconds (Standard) | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |
| 60 seconds (Conservative) | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |

---

## 6. Guidelines for the Author

1. Complete each trial in an isolated test run, restarting the target between tests if necessary to reset counters.
2. Export Prometheus range queries to CSV via `/api/v1/query_range` or Grafana CSV export to preserve raw audit trails.
3. Replace all `[TODO]` entries with verified, reproducible measurements obtained from your host system.
