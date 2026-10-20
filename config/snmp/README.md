# SNMP Exporter Configuration & MIBs Guide

## Overview

Prometheus `snmp_exporter` translates SNMP GET and WALK responses from network devices into Prometheus time-series metrics. Instead of parsing MIB files at runtime, `snmp_exporter` uses a compiled YAML configuration file (`snmp.yml`) generated ahead of time using the `snmp_exporter/generator` tool.

## Module Structure

In `snmp.yml`, configurations are organized into **modules** (e.g., `if_mib`, `synology`, `cisco_wlc`). Each module specifies:
- `walk`: List of OID prefixes to walk via SNMP (e.g., `1.3.6.1.2.1.2` for `ifTable`).
- `metrics`: Name, OID, type (`counter`, `gauge`), help string, and indexing keys for each metric.
- `version`: SNMP version (`1`, `2` for SNMPv2c, or `3`).
- `auth`: Credentials block (community string for v1/v2c, or USM parameters for v3).

## Authentication Types

### SNMPv1 / SNMPv2c (Community String)
```yaml
auth:
  community: public # or secret community string
```
*Note: In production environments, never use cleartext default community strings across untrusted networks.*

### SNMPv3 (User-based Security Model - USM)
For authenticated and encrypted transport:
```yaml
auth:
  version: 3
  username: "monitoring_user"
  security_level: "authPriv"      # noAuthNoPriv, authNoPriv, or authPriv
  auth_protocol: "SHA256"        # MD5, SHA, SHA224, SHA256, SHA384, SHA512
  auth_password: "replace-with-auth-password"
  priv_protocol: "AES128"        # DES, AES, AES192, AES256
  priv_password: "replace-with-priv-password"
```

## How to Generate or Customize `snmp.yml`

To generate a custom `snmp.yml` from vendor MIB files:

1. Clone the `snmp_exporter` generator source repository:
   ```bash
   git clone https://github.com/prometheus/snmp_exporter.git
   cd snmp_exporter/generator
   ```
2. Place proprietary vendor MIB files into `generator/mibs/`.
3. Edit `generator.yml` to specify the module name, target MIB tables, and credentials:
   ```yaml
   modules:
     custom_switch:
       walk:
         - sysUpTime
         - interfaces
         - ifXTable
       version: 2
       auth:
         community: public
   ```
4. Build and execute the generator container:
   ```bash
   docker build -t snmp-generator .
   docker run -it -v "${PWD}:/opt" snmp-generator generate
   ```
5. Copy the generated `snmp.yml` into `config/snmp/snmp.yml`.
