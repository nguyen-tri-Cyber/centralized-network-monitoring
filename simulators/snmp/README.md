# Lab SNMP Simulator Target

## Overview

This directory provides a lightweight, reproducible SNMPv2c simulator container based on `debian:bookworm-slim` and Net-SNMP (`snmpd`). It serves as an automated test target for Prometheus `snmp_exporter` without requiring physical switches or routers.

## Features

- **Standard MIB-II Support**: Implements `system` (RFC 1213) and `if-mib` / `ifMIB` (RFC 2863 `ifTable` and `ifXTable`), exposing real Linux network interfaces (`lo`, `eth0`) and operational metrics (`ifOperStatus`, `ifHCInOctets`, `ifHCOutOctets`, etc.).
- **Configurable Credentials**: Community string and system MIB metadata are controlled via environment variables (`SNMP_COMMUNITY`, `SNMP_SYS_LOCATION`, `SNMP_SYS_CONTACT`).
- **Input Sanitization**: Rejects special characters in community strings to prevent configuration injection.

## Manual Testing

You can query the simulator directly from another container or host with `snmpwalk`:

```bash
# Query system information
snmpwalk -v 2c -c public localhost:161 1.3.6.1.2.1.1

# Walk interface table (if_mib)
snmpwalk -v 2c -c public localhost:161 1.3.6.1.2.1.2
```

## Security Notice

This simulator is designed exclusively for laboratory and local testing environments. It uses cleartext SNMPv2c. Do not expose port 161/udp to public or untrusted networks.
