"""
Configuration and Schema Validation Tests.
Validates syntax, structure, and integrity of YAML configs, Docker Compose files,
Prometheus alert rules, and Grafana dashboard definitions.
"""

import json
import os
import unittest
import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestConfigurations(unittest.TestCase):
    def test_yaml_files_syntax(self):
        """All YAML configuration files in config/ and deploy/ must be valid YAML."""
        yaml_paths = [
            "deploy/docker-compose.yml",
            "docker-compose.yml",
            "config/prometheus/prometheus.yml",
            "config/prometheus/alert.rules.yml",
            "config/alertmanager/alertmanager.yml",
            "config/snmp/snmp.yml",
            "config/grafana/provisioning/datasources/prometheus.yml",
            "config/grafana/provisioning/dashboards/dashboards.yml",
        ]

        for rel_path in yaml_paths:
            full_path = os.path.join(REPO_ROOT, rel_path)
            self.assertTrue(os.path.exists(full_path), f"File {rel_path} does not exist")
            with open(full_path, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    self.assertIsNotNone(data, f"YAML file {rel_path} parsed to None")
                except yaml.YAMLError as exc:
                    self.fail(f"YAML parsing error in {rel_path}: {exc}")

    def test_docker_compose_images_pinned(self):
        """Ensure all Docker Compose service images use specific pinned tags (no 'latest')."""
        compose_path = os.path.join(REPO_ROOT, "deploy/docker-compose.yml")
        with open(compose_path, "r", encoding="utf-8") as f:
            compose = yaml.safe_load(f)

        services = compose.get("services", {})
        self.assertIn("prometheus", services)
        self.assertIn("grafana", services)
        self.assertIn("snmp-exporter", services)
        self.assertIn("alertmanager", services)
        self.assertIn("snmp-simulator", services)

        for name, spec in services.items():
            if "image" in spec:
                img = spec["image"]
                self.assertNotIn("latest", img, f"Service '{name}' image '{img}' uses 'latest' tag. Must pin specific version.")
                self.assertIn(":", img, f"Service '{name}' image '{img}' missing explicit tag.")

            # All services should have restart policy
            self.assertEqual(spec.get("restart"), "unless-stopped", f"Service '{name}' missing 'unless-stopped' restart policy")
            # All services should declare healthchecks
            self.assertIn("healthcheck", spec, f"Service '{name}' is missing healthcheck")

    def test_prometheus_alert_rules_structure(self):
        """Verify that Prometheus alert rules conform to Prometheus 2.x schema."""
        rules_path = os.path.join(REPO_ROOT, "config/prometheus/alert.rules.yml")
        with open(rules_path, "r", encoding="utf-8") as f:
            rules_doc = yaml.safe_load(f)

        self.assertIn("groups", rules_doc)
        groups = rules_doc["groups"]
        self.assertIsInstance(groups, list)
        self.assertGreater(len(groups), 0)

        alert_names = set()
        for group in groups:
            self.assertIn("name", group)
            self.assertIn("rules", group)
            for rule in group["rules"]:
                self.assertIn("alert", rule)
                self.assertIn("expr", rule)
                self.assertIn("labels", rule)
                self.assertIn("annotations", rule)
                self.assertIn("summary", rule["annotations"])
                self.assertIn("description", rule["annotations"])
                alert_names.add(rule["alert"])

        # Check required alerts from specification
        self.assertIn("SNMPTargetDown", alert_names)
        self.assertIn("NetworkInterfaceDown", alert_names)
        self.assertIn("HighInterfaceUtilization", alert_names)
        self.assertIn("InterfaceErrorsDetected", alert_names)
        self.assertIn("HighSNMPScrapeDuration", alert_names)

    def test_grafana_dashboard_json_validity(self):
        """Verify that Grafana dashboard JSON parses and uses real if_mib metrics."""
        dash_path = os.path.join(REPO_ROOT, "config/grafana/dashboards/network-overview.json")
        self.assertTrue(os.path.exists(dash_path), "Dashboard JSON not found")

        with open(dash_path, "r", encoding="utf-8") as f:
            dashboard = json.load(f)

        self.assertIn("title", dashboard)
        self.assertIn("panels", dashboard)
        self.assertGreater(len(dashboard["panels"]), 0)

        # Real if_mib metric whitelist
        valid_metric_keywords = [
            "up",
            "sysUpTime",
            "ifOperStatus",
            "ifHCInOctets",
            "ifHCOutOctets",
            "ifInErrors",
            "ifOutErrors",
            "ifInDiscards",
            "ifOutDiscards",
            "snmp_scrape_duration_seconds"
        ]

        found_queries = 0
        for panel in dashboard["panels"]:
            if "targets" in panel:
                for target in panel["targets"]:
                    expr = target.get("expr", "")
                    self.assertTrue(len(expr) > 0, f"Panel '{panel.get('title')}' has empty expr")
                    found_queries += 1
                    # Ensure query references at least one valid if_mib metric
                    has_valid_metric = any(m in expr for m in valid_metric_keywords)
                    self.assertTrue(has_valid_metric, f"Query '{expr}' does not reference any known if_mib metric")

        self.assertGreater(found_queries, 4)


if __name__ == "__main__":
    unittest.main()
