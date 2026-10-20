#!/bin/sh
set -eu

# Fallback to safe lab default community string if not provided
COMMUNITY="${SNMP_COMMUNITY:-public}"

# Sanitize community string for safety (alphanumeric, underscore, hyphen only)
case "$COMMUNITY" in
  *[!A-Za-z0-9_-]*)
    echo "[ERROR] SNMP_COMMUNITY must contain only alphanumeric characters, underscores, or hyphens." >&2
    exit 1
    ;;
esac

LOCATION="${SNMP_SYS_LOCATION:-Lab Topology - Host A1}"
CONTACT="${SNMP_SYS_CONTACT:-lab-operator@example.local}"

cat > /etc/snmp/snmpd.conf <<EOF
# Antigravity Centralized Network Monitoring - Lab SNMP Simulator Config
agentAddress udp:161

# Read-only community access for Prometheus snmp_exporter
rocommunity ${COMMUNITY}

# System MIB information
sysLocation ${LOCATION}
sysContact ${CONTACT}
sysName snmp-simulator-node01

# Enable MIB-II interfaces collection
master agentx
EOF

echo "[INFO] Starting snmpd on udp:161 with community '${COMMUNITY}'"
exec snmpd -f -Lo -C -c /etc/snmp/snmpd.conf
