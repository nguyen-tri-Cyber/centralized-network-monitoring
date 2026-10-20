FROM debian:bookworm-slim

# Install snmpd, net-snmp utilities, and networking tools for lab simulation
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        snmpd \
        snmp \
        iputils-ping \
        net-tools \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/snmp-entrypoint.sh
RUN chmod +x /usr/local/bin/snmp-entrypoint.sh

EXPOSE 161/udp

ENTRYPOINT ["/usr/local/bin/snmp-entrypoint.sh"]
