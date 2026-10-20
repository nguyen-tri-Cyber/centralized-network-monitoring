"""Controlled, evidence-producing tests for the Docker-only A1 lab."""

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import request

from .api import ZabbixAPI, ZabbixError
from .metrics import calculate_timings
from .provision import ACCOUNTS_FILE, ACTION_NAME, DASHBOARD_NAME, MAP_NAME, single
from .verify import inspect


TESTS = {
    "TC01": "Host hợp lệ được tạo và có item",
    "TC02": "Nguồn giám sát có dữ liệu mới",
    "TC03": "Ngắt endpoint tạo sự kiện sự cố",
    "TC04": "Khôi phục endpoint tạo sự kiện phục hồi",
    "TC05": "Ngắt ngắn không tạo sự cố không phù hợp",
    "TC06": "Độ trễ ICMP tăng và trigger hoạt động",
    "TC07": "Lưu lượng SNMP cập nhật sau tạo traffic",
    "TC08": "Thay đổi dung lượng đĩa lab được ghi nhận",
    "TC09": "Mailpit nhận email từ action sự cố",
    "TC10": "Viewer bị từ chối sửa host",
    "TC11": "Zabbix Server khởi động lại và giữ dữ liệu",
    "TC12": "Lịch sử sự kiện tra cứu được",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_mail_time(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def newest_event_after(events: list[dict], known_ids: set[str], start: int):
    candidates = [row for row in events if row["eventid"] not in known_ids
                  and int(row["clock"]) >= start]
    return max(candidates, key=lambda row: (int(row["clock"]), int(row["eventid"])), default=None)


def docker(project_dir: Path, *args: str) -> str:
    cmd = ["docker", "compose", *args]
    result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError(f"{' '.join(cmd)} failed: {result.stderr.strip()[:500]}")
    return result.stdout.strip()


def wait_for(label: str, predicate, timeout: int, interval: int = 5):
    deadline = time.monotonic() + timeout
    next_report = time.monotonic() + 30
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        if time.monotonic() >= next_report:
            print(f"  Waiting for {label}...", flush=True)
            next_report += 30
        time.sleep(interval)
    return None


def host_id(api, name: str) -> str:
    host = single(api, "host.get", "host", name, ["hostid", "host"])
    if not host:
        raise RuntimeError(f"Host missing: {name}; run provision first")
    return host["hostid"]


def trigger_id(api, hostid: str, description: str) -> str:
    rows = api.call("trigger.get", {"hostids": hostid, "output": ["triggerid", "description"],
                                    "filter": {"description": [description]}})
    if len(rows) != 1:
        raise RuntimeError(f"Expected one trigger: {description}; found {len(rows)}")
    return rows[0]["triggerid"]


def events(api, triggerid: str, start: int = 0, value: int | None = None) -> list[dict]:
    params = {"objectids": triggerid, "source": 0, "object": 0,
              "output": ["eventid", "clock", "name", "value", "r_eventid"],
              "sortfield": ["clock", "eventid"], "sortorder": "DESC", "limit": 100}
    if start:
        params["time_from"] = start
    if value is not None:
        params["value"] = value
    return api.call("event.get", params)


def item(api, hostid: str, key: str):
    rows = api.call("item.get", {"hostids": hostid, "output": ["itemid", "key_", "lastvalue", "lastclock"],
                                 "filter": {"key_": [key]}})
    return rows[0] if rows else None


def mailpit_messages() -> list[dict]:
    with request.urlopen("http://127.0.0.1:8025/api/v1/messages", timeout=10) as response:
        return json.load(response).get("messages", [])


def mail_after(start: int, marker: str):
    for row in mailpit_messages():
        subject = str(row.get("Subject", row.get("subject", "")))
        created = row.get("Created", row.get("created", ""))
        if marker in subject and created and parse_mail_time(created) >= start:
            return row
    return None


def record(code: str, success: bool, actual, evidence=None) -> dict:
    return {"id": code, "objective": TESTS[code], "status": "PASS" if success else "FAIL",
            "executed_at_utc": utc_now(), "expected": TESTS[code], "actual": actual,
            "evidence": evidence or {}}


def quick_cases(api, project_dir: Path) -> list[dict]:
    hostids = {name: host_id(api, name) for name in
               ("A1-LAB-ENDPOINT", "lab-linux-agent", "A1-LAB-SNMP")}
    counts = {name: int(api.call("item.get", {"hostids": hid, "countOutput": True}))
              for name, hid in hostids.items()}
    tc01 = record("TC01", len(hostids) == 3 and all(count > 0 for count in counts.values()), counts)
    check = inspect(api, project_dir)
    tc02 = record("TC02", all(row["status"] == "PASS" for row in check["items"].values()),
                  check["items"], {"verification": check["checked_at_utc"]})
    return [tc01, tc02]


def short_fault(api, project_dir: Path) -> dict:
    hid = host_id(api, "A1-LAB-ENDPOINT")
    tid = trigger_id(api, hid, "ICMP Ping: Unavailable by ICMP ping")
    before = {row["eventid"] for row in events(api, tid, value=1)}
    start = int(time.time())
    try:
        docker(project_dir, "stop", "lab-endpoint")
        time.sleep(5)
    finally:
        docker(project_dir, "start", "lab-endpoint")
    # Three failed one-minute samples are required; wait beyond two checks.
    time.sleep(130)
    new = newest_event_after(events(api, tid, start, 1), before, start)
    return record("TC05", new is None, "No new outage event" if new is None else new,
                  {"fault_at": start, "duration_seconds": 5})


def outage_cases(api, project_dir: Path) -> list[dict]:
    hid = host_id(api, "A1-LAB-ENDPOINT")
    tid = trigger_id(api, hid, "ICMP Ping: Unavailable by ICMP ping")
    action = single(api, "action.get", "name", ACTION_NAME, ["actionid", "name"])
    before = {row["eventid"] for row in events(api, tid, value=1)}
    fault_at = int(time.time())
    problem = None
    recovery = None
    message = None
    alert = None
    try:
        print("  Stopping lab-endpoint; waiting up to 4 minutes for three failed ICMP checks.", flush=True)
        docker(project_dir, "stop", "lab-endpoint")
        problem = wait_for("outage event", lambda: newest_event_after(events(api, tid, fault_at, 1), before, fault_at), 250)
        if problem:
            message = wait_for("Mailpit problem email", lambda: mail_after(fault_at, "A1 LAB PROBLEM"), 45)
            if action:
                alert = wait_for("Zabbix sent alert", lambda: next(
                    (row for row in api.call("alert.get", {"eventids": problem["eventid"],
                                                            "actionids": action["actionid"],
                                                            "output": ["alertid", "clock", "status", "error"]})
                     if str(row["status"]) == "1"), None), 30)
    finally:
        docker(project_dir, "start", "lab-endpoint")
    restored_at = int(time.time())
    if problem:
        def recovery_event():
            rows = api.call("event.get", {"eventids": [problem["eventid"]],
                                          "output": ["eventid", "r_eventid"]})
            recovery_id = rows[0].get("r_eventid", "0") if rows else "0"
            if recovery_id == "0":
                return None
            return api.call("event.get", {"eventids": [recovery_id],
                                          "output": ["eventid", "clock", "name", "value"]})[0]
        recovery = wait_for("recovery event", recovery_event, 240)
    event_at = int(problem["clock"]) if problem else None
    mail_at = parse_mail_time(message.get("Created", message.get("created"))) if message else None
    timing = calculate_timings(fault_at, event_at, mail_at)
    evidence = {"fault_at": fault_at, "eventid": problem["eventid"] if problem else None,
                "recovery_eventid": recovery["eventid"] if recovery else None,
                "restored_at": restored_at, "mail_id": message.get("ID", message.get("id")) if message else None,
                **timing}
    return [
        record("TC03", bool(problem), problem or "No event before timeout", evidence),
        record("TC04", bool(recovery), recovery or "No recovery before timeout", evidence),
        record("TC09", bool(message and alert), {"mail": bool(message), "alert": alert}, evidence),
        record("TC12", bool(problem and recovery), "Stored problem and recovery event" if recovery else "Event history missing", evidence),
    ]


def latency_case(api, project_dir: Path) -> dict:
    hid = host_id(api, "A1-LAB-ENDPOINT")
    tid = trigger_id(api, hid, "A1 Lab: ICMP latency above 200 ms (2 checks)")
    before = {row["eventid"] for row in events(api, tid, value=1)}
    started = int(time.time())
    try:
        print("  Adding 500 ms one-way delay inside lab-endpoint.", flush=True)
        docker(project_dir, "exec", "-T", "lab-endpoint", "tc", "qdisc", "replace", "dev", "eth0",
               "root", "netem", "delay", "500ms")
        problem = wait_for("latency event", lambda: newest_event_after(events(api, tid, started, 1), before, started), 190)
        rtt = item(api, hid, "icmppingsec")
    finally:
        docker(project_dir, "exec", "-T", "lab-endpoint", "tc", "qdisc", "del", "dev", "eth0", "root")
    success = bool(problem) and rtt is not None and float(rtt["lastvalue"]) > 0.2
    return record("TC06", success, {"problem": problem, "response_seconds": rtt["lastvalue"] if rtt else None},
                  {"delay_started_at": started})


def traffic_case(api, project_dir: Path) -> dict:
    hid = host_id(api, "A1-LAB-SNMP")
    rows = api.call("item.get", {"hostids": hid,
                                 "output": ["itemid", "key_", "lastvalue", "lastclock"]})
    counter = next((row for row in rows if row["key_"].startswith("net.if.in[")), None)
    if counter is None:
        return record("TC07", False, "SNMP interface item not discovered")
    prior_clock = int(counter["lastclock"] or 0)
    docker(project_dir, "exec", "-T", "lab-snmp", "ping", "-c", "100", "-i", "0.05", "-s", "1000", "zabbix-server")
    def updated():
        found = api.call("item.get", {"itemids": [counter["itemid"]],
                                       "output": ["itemid", "lastclock", "lastvalue"]})
        return found[0] if found and int(found[0]["lastclock"] or 0) > prior_clock else None
    latest = wait_for("new SNMP traffic sample", updated, 130)
    success = latest is not None and float(latest["lastvalue"]) > float(counter["lastvalue"])
    return record("TC07", success, {"before": counter["lastvalue"],
                                    "after": latest["lastvalue"] if latest else None},
                  {"itemid": counter["itemid"], "before_clock": prior_clock,
                   "after_clock": latest["lastclock"] if latest else None})


def disk_case(api, project_dir: Path) -> dict:
    hid = host_id(api, "lab-linux-agent")
    old = item(api, hid, "vfs.fs.size[/,pused]")
    if old is None:
        return record("TC08", False, "Root disk item missing")
    file_path = "/tmp/a1-lab-disk-test.bin"
    try:
        docker(project_dir, "exec", "-T", "lab-agent", "dd", "if=/dev/zero", f"of={file_path}", "bs=1M", "count=128")
        def updated():
            current = item(api, hid, "vfs.fs.size[/,pused]")
            return current if current and int(current["lastclock"] or 0) > int(old["lastclock"] or 0) else None
        current = wait_for("new disk usage sample", updated, 130)
    finally:
        docker(project_dir, "exec", "-T", "lab-agent", "rm", "-f", file_path)
    success = current is not None and float(current["lastvalue"]) > float(old["lastvalue"])
    return record("TC08", success, {"before_percent": old["lastvalue"],
                                    "after_percent": current["lastvalue"] if current else None},
                  {"itemid": old["itemid"], "temporary_bytes": 128 * 1024 * 1024})


def permission_case(api, project_dir: Path, base_url: str) -> dict:
    accounts = json.loads((project_dir / ACCOUNTS_FILE).read_text(encoding="utf-8"))
    target = single(api, "host.get", "host", "A1-LAB-ENDPOINT", ["hostid", "host", "name"])
    if not target:
        return record("TC10", False, "A1 Lab endpoint missing")
    # Admin first proves this harmless, unchanged-name update is valid API input.
    update = {"hostid": target["hostid"], "name": target["name"]}
    api.call("host.update", update)
    viewer = ZabbixAPI(base_url)
    try:
        viewer.login("a1-viewer", accounts["a1-viewer"])
        visible = viewer.call("host.get", {"output": ["hostid"],
                                           "filter": {"host": ["A1-LAB-ENDPOINT"]}})
        dashboard = single(viewer, "dashboard.get", "name", DASHBOARD_NAME, ["dashboardid", "name"])
        host_map = single(viewer, "map.get", "name", MAP_NAME, ["sysmapid", "name"])
        denied = False
        error_message = ""
        try:
            viewer.call("host.update", update)
        except ZabbixError as exc:
            error_message = str(exc)
            denied = True
        return record("TC10", bool(visible) and bool(dashboard) and bool(host_map) and denied,
                      {"lab_host_visible": bool(visible), "dashboard_visible": bool(dashboard),
                       "map_visible": bool(host_map), "configuration_denied": denied,
                       "admin_validated_update_payload": True,
                       "api_response": error_message})
    finally:
        viewer.logout()


def restart_case(api, project_dir: Path) -> dict:
    hid = host_id(api, "A1-LAB-ENDPOINT")
    old = item(api, hid, "icmpping")
    if not old or not old.get("lastclock"):
        return record("TC11", False, "ICMP baseline missing before restart")
    docker(project_dir, "restart", "zabbix-server")
    def new_sample():
        try:
            current = item(api, hid, "icmpping")
        except ZabbixError:
            return None
        return current if current and int(current["lastclock"] or 0) > int(old["lastclock"]) else None
    current = wait_for("fresh ICMP sample after Zabbix Server restart", new_sample, 180)
    history = api.call("history.get", {"itemids": [old["itemid"]], "history": 3,
                                       "time_from": int(old["lastclock"]), "time_till": int(old["lastclock"]),
                                       "output": ["clock", "value"], "limit": 10}) if current else []
    preserved = any(row["clock"] == old["lastclock"] and row["value"] == old["lastvalue"] for row in history)
    success = bool(current and str(current["lastvalue"]) == "1" and preserved)
    return record("TC11", success,
                  {"previous_clock": old["lastclock"], "current_clock": current["lastclock"] if current else None,
                   "current_value": current["lastvalue"] if current else None,
                   "old_sample_preserved": preserved})


def run_cases(api, project_dir: Path, base_url: str, selected: str) -> dict:
    requested = set(TESTS) if selected == "all" else {selected}
    results = []

    def capture(codes: tuple[str, ...], run):
        try:
            results.extend(row for row in run() if row["id"] in codes)
        except Exception as exc:
            # Infrastructure/API errors are test failures with evidence, not missing reports.
            for code in codes:
                results.append(record(code, False, f"{type(exc).__name__}: {str(exc)[:500]}",
                                      {"error_type": type(exc).__name__}))

    if requested & {"TC01", "TC02"}:
        capture(tuple(code for code in ("TC01", "TC02") if code in requested),
                lambda: quick_cases(api, project_dir))
    if "TC05" in requested:
        print("TC05: short interruption", flush=True)
        capture(("TC05",), lambda: [short_fault(api, project_dir)])
    if requested & {"TC03", "TC04", "TC09", "TC12"}:
        print("TC03/04/09/12: outage, recovery and email", flush=True)
        # One controlled fault produces four independently verified outcomes.
        capture(("TC03", "TC04", "TC09", "TC12"), lambda: outage_cases(api, project_dir))
    if "TC06" in requested:
        print("TC06: latency", flush=True)
        capture(("TC06",), lambda: [latency_case(api, project_dir)])
    if "TC07" in requested:
        print("TC07: SNMP traffic", flush=True)
        capture(("TC07",), lambda: [traffic_case(api, project_dir)])
    if "TC08" in requested:
        print("TC08: Linux disk usage", flush=True)
        capture(("TC08",), lambda: [disk_case(api, project_dir)])
    if "TC10" in requested:
        print("TC10: viewer permission", flush=True)
        capture(("TC10",), lambda: [permission_case(api, project_dir, base_url)])
    if "TC11" in requested:
        print("TC11: server restart", flush=True)
        capture(("TC11",), lambda: [restart_case(api, project_dir)])
    expected = requested | ({"TC03", "TC04", "TC09", "TC12"} if requested & {"TC03", "TC04", "TC09", "TC12"} else set())
    observed = {row["id"] for row in results}
    for code in sorted(expected - observed):
        results.append(record(code, False, "Test runner returned no result"))
    results.sort(key=lambda row: row["id"])
    return {"checked_at_utc": utc_now(), "scope": "Docker lab only", "pass": all(row["status"] == "PASS" for row in results),
            "cases": results}


def save_cases(report: dict, project_dir: Path) -> tuple[Path, Path]:
    output = project_dir / "output"
    output.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output / f"test-run-{stamp}.json"
    md_path = output / f"test-run-{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# A1 Lab — kết quả kiểm thử", "", f"Thời điểm UTC: {report['checked_at_utc']}",
             f"Kết luận: {'PASS' if report['pass'] else 'FAIL'}", "",
             "| Mã | Kết quả | Mục tiêu |", "|---|---|---|"]
    lines += [f"| {row['id']} | {row['status']} | {row['objective']} |" for row in report["cases"]]
    lines += ["", "Chi tiết thực tế và minh chứng nằm trong tệp JSON cùng tên. Kết quả chỉ đại diện lab Docker."]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
