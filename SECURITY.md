# Security Policy

## Laboratory & Educational Scope

This project is developed as an academic undergraduate thesis and laboratory demonstration. It is **not hardened for production deployment**.

### Key Security Caveats:
1. **Unencrypted SNMPv2c**: The current implementation utilizes cleartext SNMPv2c community strings. Community strings are transmitted in cleartext over UDP port 161. Do not deploy this configuration across untrusted or public networks.
2. **Web Consoles**: Prometheus (`:9090`) and Alertmanager (`:9093`) run without built-in authentication by default. Grafana (`:3000`) uses default laboratory admin credentials which must be changed before any deployment beyond `localhost`.
3. **No TLS / HTTPS**: The internal microservices communicate over unencrypted HTTP. Production deployments must place these services behind an authenticating TLS reverse proxy (e.g., Traefik, Nginx, Caddy).

---

## Reporting Vulnerabilities

If you discover a security vulnerability or sensitive information leakage within this repository:

1. **Do not open a public issue.**
2. Send an email to the project maintainer at `trint0607@ut.edu.vn`.

3. Provide details of the issue, affected files, and reproducible steps.
