#!/bin/sh
set -eu

: "${SNMP_COMMUNITY:?SNMP_COMMUNITY is required}"
case "$SNMP_COMMUNITY" in
  *[!A-Za-z0-9_-]*)
    echo "SNMP_COMMUNITY must use only letters, digits, _ or -" >&2
    exit 1
    ;;
esac

cat > /etc/snmp/snmpd.conf <<EOF
agentAddress udp:161
rocommunity ${SNMP_COMMUNITY}
sysLocation A1 Docker lab
sysContact local-lab
EOF

exec snmpd -f -Lo -C -c /etc/snmp/snmpd.conf

