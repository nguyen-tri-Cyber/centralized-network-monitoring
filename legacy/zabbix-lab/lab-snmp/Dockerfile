FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends snmpd snmp iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/a1-snmp-entrypoint
RUN chmod +x /usr/local/bin/a1-snmp-entrypoint

EXPOSE 161/udp
ENTRYPOINT ["/usr/local/bin/a1-snmp-entrypoint"]
