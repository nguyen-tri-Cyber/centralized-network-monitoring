#!/usr/bin/env python3
"""
Validation script for Centralized Network Monitoring System.
Performs linting, schema checking, and executes test suites.
Can be run on Linux, macOS, and Windows.
"""

import json
import os
import subprocess
import sys
import unittest
import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)



def print_step(title: str):
    print(f"\n{'='*70}\n[STEP] {title}\n{'='*70}")


def check_yaml_files() -> bool:
    print_step("Validating YAML Configuration Syntax")
    yaml_files = [
        "deploy/docker-compose.yml",
        "docker-compose.yml",
        "config/prometheus/prometheus.yml",
        "config/prometheus/alert.rules.yml",
        "config/alertmanager/alertmanager.yml",
        "config/snmp/snmp.yml",
        "config/grafana/provisioning/datasources/prometheus.yml",
        "config/grafana/provisioning/dashboards/dashboards.yml",
    ]

    all_passed = True
    for rel_path in yaml_files:
        full_path = os.path.join(REPO_ROOT, rel_path)
        if not os.path.exists(full_path):
            print(f"  [MISSING] {rel_path}")
            all_passed = False
            continue
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
            print(f"  [PASS] {rel_path}")
        except Exception as e:
            print(f"  [FAIL] {rel_path}: {e}")
            all_passed = False

    return all_passed


def check_grafana_dashboards() -> bool:
    print_step("Validating Grafana Dashboard JSON Syntax")
    dashboards = ["config/grafana/dashboards/network-overview.json"]
    all_passed = True
    for rel_path in dashboards:
        full_path = os.path.join(REPO_ROOT, rel_path)
        if not os.path.exists(full_path):
            print(f"  [MISSING] {rel_path}")
            all_passed = False
            continue
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            panels = data.get("panels", [])
            print(f"  [PASS] {rel_path} (Valid JSON, {len(panels)} panels)")
        except Exception as e:
            print(f"  [FAIL] {rel_path}: {e}")
            all_passed = False
    return all_passed


def run_unit_tests() -> bool:
    print_step("Running Python Unit Tests")
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(REPO_ROOT, "tests"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


def check_docker_compose_and_promtool() -> None:
    print_step("Checking Docker Daemon & Promtool Validation")
    # Check if Docker is responding
    try:
        proc = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
        docker_available = (proc.returncode == 0)
    except Exception:
        docker_available = False

    if not docker_available:
        print("  [INFO] Docker daemon is not running or accessible on this host.")
        print("  [INFO] Skipping local container-based validation (docker compose config, promtool).")
        print("  [INFO] Note: These checks are automated in CI (.github/workflows/ci.yml).")
        return

    # If docker is running:
    print("  [INFO] Docker daemon is active. Running 'docker compose config'...")
    compose_path = os.path.join(REPO_ROOT, "deploy/docker-compose.yml")
    res = subprocess.run(["docker", "compose", "-f", compose_path, "config", "-q"], capture_output=True, text=True)
    if res.returncode == 0:
        print("  [PASS] 'docker compose config' is valid.")
    else:
        print(f"  [FAIL] 'docker compose config' failed: {res.stderr}")

    print("  [INFO] Running promtool check config inside Prometheus container...")
    prom_cfg = os.path.join(REPO_ROOT, "config/prometheus/prometheus.yml")
    prom_rules = os.path.join(REPO_ROOT, "config/prometheus/alert.rules.yml")
    pt_res = subprocess.run([
        "docker", "run", "--rm",
        "-v", f"{REPO_ROOT}/config/prometheus:/etc/prometheus:ro",
        "prom/prometheus:v2.54.1",
        "promtool", "check", "config", "/etc/prometheus/prometheus.yml"
    ], capture_output=True, text=True)

    if pt_res.returncode == 0:
        print("  [PASS] promtool check config passed.")
    else:
        print(f"  [WARN] promtool output: {pt_res.stderr or pt_res.stdout}")


def main() -> int:
    yaml_ok = check_yaml_files()
    dash_ok = check_grafana_dashboards()
    tests_ok = run_unit_tests()
    check_docker_compose_and_promtool()

    print_step("Validation Summary")
    print(f"  YAML Configs:        {'PASS' if yaml_ok else 'FAIL'}")
    print(f"  Grafana Dashboards:  {'PASS' if dash_ok else 'FAIL'}")
    print(f"  Unit Tests:          {'PASS' if tests_ok else 'FAIL'}")

    if yaml_ok and dash_ok and tests_ok:
        print("\n[SUCCESS] All baseline validations and unit tests passed!")
        return 0
    else:
        print("\n[FAILURE] One or more validations failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
