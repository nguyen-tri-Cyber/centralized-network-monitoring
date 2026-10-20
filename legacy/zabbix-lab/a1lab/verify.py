"""Read-only checks and evidence export for the running lab."""

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .provision import ACTION_NAME, DASHBOARD_NAME, MAP_NAME, MEDIA_NAME, single


EXPECTED_HOSTS = ("A1-LAB-ENDPOINT", "lab-linux-agent", "A1-LAB-SNMP")


def evaluate_item(item: dict | None, now: int, max_age: int = 300) -> dict:
    if item is None:
        return {"status": "FAIL", "reason": "item missing"}
    if str(item.get("status")) != "0" or str(item.get("state")) != "0":
        return {"status": "FAIL", "reason": "item disabled or unsupported", "error": item.get("error", "")}
    clock = int(item.get("lastclock") or 0)
    if clock == 0:
        return {"status": "FAIL", "reason": "no value yet"}
    age = now - clock
    if age > max_age or age < -60:
        return {"status": "FAIL", "reason": f"stale value ({age}s old)", "lastclock": clock}
    return {"status": "PASS", "value": item.get("lastvalue"), "lastclock": clock, "age_seconds": age}


def docker_services(project_dir: Path) -> dict:
    try:
        result = subprocess.run(["docker", "compose", "ps", "--format", "json"], cwd=project_dir,
                                capture_output=True, text=True, timeout=30, check=True)
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        return {row["Service"]: {"state": row["State"], "health": row.get("Health", "")} for row in rows}
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return {}


def inspect(api, project_dir: Path, max_age: int = 300) -> dict:
    now = int(time.time())
    group = single(api, "hostgroup.get", "name", "A1 Lab", ["groupid", "name"])
    hosts = {name: single(api, "host.get", "host", name,
                          ["hostid", "host", "status", "available", "snmp_available"])
             for name in EXPECTED_HOSTS}
    items_by_host = {}
    for name, host in hosts.items():
        items_by_host[name] = api.call("item.get", {"hostids": host["hostid"],
                                                  "output": ["itemid", "key_", "name", "lastvalue",
                                                             "lastclock", "state", "status", "error"]}) if host else []

    def exact(name, key):
        return next((row for row in items_by_host[name] if row["key_"] == key), None)

    checks = {
        "ICMP availability": exact("A1-LAB-ENDPOINT", "icmpping"),
        "ICMP loss": exact("A1-LAB-ENDPOINT", "icmppingloss"),
        "ICMP response": exact("A1-LAB-ENDPOINT", "icmppingsec"),
        "Linux CPU": exact("lab-linux-agent", "system.cpu.util"),
        "Linux RAM available": exact("lab-linux-agent", "vm.memory.size[pavailable]"),
        "Linux root disk used": exact("lab-linux-agent", "vfs.fs.size[/,pused]"),
        "SNMP interface in": next((row for row in items_by_host["A1-LAB-SNMP"]
                                    if row["key_"].startswith("net.if.in[")), None),
        "SNMP interface out": next((row for row in items_by_host["A1-LAB-SNMP"]
                                     if row["key_"].startswith("net.if.out[")), None),
    }
    item_results = {name: evaluate_item(item, now, max_age) for name, item in checks.items()}
    objects = {
        "host_group": bool(group),
        "hosts": {name: bool(host) and str(host["status"]) == "0" for name, host in hosts.items()},
        "dashboard": bool(single(api, "dashboard.get", "name", DASHBOARD_NAME, ["dashboardid", "name"])),
        "map": bool(single(api, "map.get", "name", MAP_NAME, ["sysmapid", "name"])),
        "mail_media": bool(single(api, "mediatype.get", "name", MEDIA_NAME, ["mediatypeid", "name"])),
        "action": bool(single(api, "action.get", "name", ACTION_NAME, ["actionid", "name"])),
        "operator": bool(single(api, "user.get", "username", "a1-operator", ["userid", "username"])),
        "viewer": bool(single(api, "user.get", "username", "a1-viewer", ["userid", "username"])),
    }
    services = docker_services(project_dir)
    expected_services = ("db", "zabbix-server", "web", "lab-agent", "lab-snmp", "lab-endpoint", "mailpit")
    services_ok = all(services.get(name, {}).get("state") == "running" for name in expected_services)
    passed = all(objects["hosts"].values()) and all(value for key, value in objects.items() if key != "hosts")
    passed = passed and all(row["status"] == "PASS" for row in item_results.values()) and services_ok
    return {"checked_at_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "zabbix_version": api.call("apiinfo.version"), "pass": passed,
            "objects": objects, "items": item_results, "services": services}


def save_report(report: dict, project_dir: Path, prefix: str = "verify") -> tuple[Path, Path]:
    output = project_dir / "output"
    output.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output / f"{prefix}-{stamp}.json"
    md_path = output / f"{prefix}-{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [f"# A1 Lab — {prefix}", "", f"Thời điểm UTC: {report.get('checked_at_utc', '')}",
             f"Kết luận: {'PASS' if report.get('pass') else 'FAIL'}", ""]
    if "items" in report:
        lines += ["| Chỉ số | Trạng thái | Giá trị | Ghi chú |", "|---|---|---|---|"]
        for name, item in report["items"].items():
            lines.append(f"| {name} | {item['status']} | {item.get('value', '')} | {item.get('reason', '')} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
