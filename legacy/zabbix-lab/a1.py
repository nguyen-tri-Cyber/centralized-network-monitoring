"""CLI for provisioning and validating the local A1 monitoring lab."""

import argparse
import getpass
import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlparse

from a1lab.api import ZabbixAPI, ZabbixError
from a1lab.provision import ACCOUNTS_FILE, provision
from a1lab.verify import inspect, save_report
from a1lab.scenarios import TESTS, run_cases, save_cases
from a1lab.report import (collect_case_runs, operational_report, save_case_summary,
                          save_operational_report)


PROJECT_DIR = Path(__file__).resolve().parent


def admin_password() -> str:
    password = os.environ.get("A1_ADMIN_PASSWORD")
    if password:
        return password
    path = PROJECT_DIR / ACCOUNTS_FILE
    if path.exists():
        accounts = json.loads(path.read_text(encoding="utf-8"))
        password = accounts.get("Admin_pending") or accounts.get("Admin")
        if password:
            return password
    if not sys.stdin.isatty():
        raise ZabbixError("Set A1_ADMIN_PASSWORD for noninteractive commands or run secure-admin interactively")
    return getpass.getpass("Zabbix Admin password: ")


def is_local_zabbix(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")


def save_accounts(accounts: dict) -> None:
    path = PROJECT_DIR / ACCOUNTS_FILE
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(accounts, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def secure_admin(api: ZabbixAPI, current_password: str) -> None:
    path = PROJECT_DIR / ACCOUNTS_FILE
    accounts = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    admin = api.call("user.get", {"output": ["userid", "username"],
                                  "filter": {"username": ["Admin"]}})
    if len(admin) != 1:
        raise ZabbixError("Expected exactly one Admin user")
    replacement = secrets.token_urlsafe(32)
    accounts["Admin_pending"] = replacement
    save_accounts(accounts)
    try:
        api.call("user.update", {"userid": admin[0]["userid"], "passwd": replacement,
                                 "current_passwd": current_password})
    except (ZabbixError, OSError):
        accounts.pop("Admin_pending", None)
        save_accounts(accounts)
        raise
    accounts["Admin"] = replacement
    accounts.pop("Admin_pending", None)
    save_accounts(accounts)
    verify = ZabbixAPI(api.url.removesuffix("/api_jsonrpc.php"))
    try:
        verify.login("Admin", replacement)
    finally:
        try:
            verify.logout()
        except ZabbixError:
            pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="A1 centralized monitoring lab")
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="Local Zabbix URL")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("provision", help="Create or update Zabbix lab objects")
    sub.add_parser("secure-admin", help="Replace default Admin password with a local random password")
    verify_parser = sub.add_parser("verify", help="Check live items and save evidence")
    verify_parser.add_argument("--max-age", type=int, default=300, help="Maximum age of a metric in seconds")
    test_parser = sub.add_parser("test", help="Run controlled TC01-TC12 lab scenarios")
    test_parser.add_argument("--case", choices=["all", *TESTS], default="all")
    report_parser = sub.add_parser("report", help="Export observed metrics and event statistics")
    report_parser.add_argument("--hours", type=int, default=24, help="Observation window, 1-168 hours")
    sub.add_parser("summarize", help="Merge the latest saved evidence for TC01-TC12")
    args = parser.parse_args(argv)
    if not is_local_zabbix(args.url):
        parser.error("A1 lab commands only accept a local HTTP Zabbix URL")
    if args.command == "summarize":
        try:
            result = collect_case_runs(PROJECT_DIR)
            json_path, md_path = save_case_summary(result, PROJECT_DIR)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"{'PASS' if result['pass'] else 'INCOMPLETE/FAIL'}: {md_path}\nRaw summary: {json_path}")
        return 0 if result["pass"] else 2
    api = ZabbixAPI(args.url)
    try:
        version = api.call("apiinfo.version")
        if not version.startswith("7.4."):
            raise ZabbixError(f"This source targets Zabbix 7.4; server is {version}")
        password = admin_password()
        api.login("Admin", password)
        if args.command == "provision":
            result = provision(api, PROJECT_DIR)
            print(json.dumps(result, indent=2))
            print("Demo account passwords: local-accounts.json (keep this file private).")
        elif args.command == "secure-admin":
            secure_admin(api, password)
            print("Admin password rotated and stored in local-accounts.json. Log in again if the web session expired.")
        elif args.command == "verify":
            result = inspect(api, PROJECT_DIR, args.max_age)
            json_path, md_path = save_report(result, PROJECT_DIR)
            print(f"{'PASS' if result['pass'] else 'FAIL'}: {json_path}")
            for name, item in result["items"].items():
                print(f"  {item['status']}: {name} {item.get('value', item.get('reason', ''))}")
            print(f"Readable report: {md_path}")
            return 0 if result["pass"] else 2
        elif args.command == "test":
            result = run_cases(api, PROJECT_DIR, args.url, args.case)
            json_path, md_path = save_cases(result, PROJECT_DIR)
            for row in result["cases"]:
                print(f"{row['id']}: {row['status']}")
            print(f"Evidence: {json_path}\nSummary: {md_path}")
            return 0 if result["pass"] else 2
        elif args.command == "report":
            result, samples = operational_report(api, args.hours)
            json_path, md_path, csv_path = save_operational_report(result, samples, PROJECT_DIR)
            print(f"Operational report: {md_path}\nStatistics: {json_path}\nRaw samples: {csv_path}")
            return 0 if result["complete"] else 2
        return 0
    except (ZabbixError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            api.logout()
        except ZabbixError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
